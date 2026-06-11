from __future__ import annotations

import secrets
import tempfile
import time
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import __version__
from .analyzer import OBJECTIVE, analyze_manuscript, get_ai_review_protocol_blueprint, get_check_definitions
from .config import (
    allowed_cors_origins,
    configured_api_keys,
    cors_allow_credentials,
    rate_limit_key_source,
    rate_limit_per_minute,
    require_api_key,
    retention_days,
    trust_forwarded_for,
    upload_limit_bytes,
)
from .image_inspect import SUPPORTED_IMAGE_SUFFIXES, inspect_image, is_supported_image
from .models import RunReport, RunRequest
from .pdf import PDFDependencyUnavailableError, PDFTextExtractionError, extract_text_from_pdf
from .pdf_inspect import inspect_pdf
from .sarif import report_to_sarif
from .store import ReportStore, SubmissionConflictError

app = FastAPI(
    title="OpenRI API",
    version=__version__,
    description="OSS research-integrity test runner for manuscripts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE = ReportStore()
RATE_BUCKETS: dict[str, list[float]] = {}
RATE_LIMIT_IDENTITY_SALTS = (secrets.token_hex(16), secrets.token_hex(16))


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".tex", ".rst"}
UPLOAD_SUFFIXES = TEXT_SUFFIXES | {".pdf"} | SUPPORTED_IMAGE_SUFFIXES
UPLOAD_READ_CHUNK_BYTES = 1024 * 1024
MULTIPART_OVERHEAD_ALLOWANCE_BYTES = 64 * 1024


class SubmissionStatusUpdate(BaseModel):
    status: Literal[
        "editorial_hold",
        "queued_for_editor_check",
        "statistics_review",
        "technical_check",
        "ready_for_peer_review",
        "returned_to_author",
        "rejected",
    ]
    actor: str = "openri"


def _sanitize_filename(filename: Optional[str]) -> str:
    name = Path(filename or "uploaded-manuscript.txt").name
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "_" for ch in name).strip()
    return cleaned[:160] or "uploaded-manuscript.txt"


def _looks_like_pdf(payload: bytes) -> bool:
    return payload.startswith(b"%PDF-")


def _looks_like_image(payload: bytes) -> bool:
    signatures = (
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"RIFF",
        b"II*\x00",
        b"MM\x00*",
        b"BM",
    )
    return payload.startswith(signatures)


def _validate_upload(filename: str, content_type: Optional[str], payload: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_file_type",
                "allowed_extensions": sorted(UPLOAD_SUFFIXES),
                "filename": filename,
            },
        )
    if suffix == ".pdf" and not _looks_like_pdf(payload):
        raise HTTPException(status_code=422, detail={"error": "invalid_pdf_magic", "filename": filename})
    if suffix in SUPPORTED_IMAGE_SUFFIXES and not _looks_like_image(payload):
        raise HTTPException(status_code=422, detail={"error": "invalid_image_magic", "filename": filename})
    if suffix in TEXT_SUFFIXES and content_type:
        media_type = content_type.split(";", 1)[0].strip().lower()
        is_allowed_text = media_type.startswith("text/") or media_type in {
            "application/octet-stream",
            "application/x-latex",
            "application/x-tex",
        }
        if not is_allowed_text:
            raise HTTPException(
                status_code=422, detail={"error": "invalid_text_content_type", "content_type": content_type}
            )
    return suffix


async def _read_upload_form(request: Request):
    limit = upload_limit_bytes()
    raw_content_length = request.headers.get("content-length")
    if raw_content_length:
        try:
            content_length = int(raw_content_length)
        except ValueError:
            content_length = None
        if content_length is not None and content_length > limit + MULTIPART_OVERHEAD_ALLOWANCE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"error": "request_too_large", "limit_bytes": limit, "content_length": content_length},
            )
    try:
        try:
            form = await request.form(max_files=1, max_fields=20, max_part_size=limit)
        except TypeError:
            form = await request.form(max_files=1, max_fields=20)
    except (AssertionError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "multipart_support_unavailable",
                "message": "Install OpenRI with the server extra on Python 3.10 or newer to enable file uploads.",
            },
        ) from exc
    file = form.get("file")
    if file is None or not hasattr(file, "read"):
        raise HTTPException(status_code=422, detail={"error": "missing_upload_file", "field": "file"})
    return form, file


async def _read_upload_payload(file, limit: int) -> bytes:
    payload = bytearray()
    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > limit:
            raise HTTPException(status_code=413, detail={"error": "file_too_large", "limit_bytes": limit})
    return bytes(payload)


def _form_text(form, key: str, default: str) -> str:
    value = form.get(key)
    if value is None:
        return default
    return str(value)


def _form_bool(form, key: str, default: bool = False) -> bool:
    value = form.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _api_key_is_configured(api_key: Optional[str]) -> bool:
    if not api_key:
        return False
    return any(secrets.compare_digest(api_key, configured_key) for configured_key in configured_api_keys())


def _require_api_key(x_openri_api_key: Optional[str] = Header(default=None)) -> None:
    if not require_api_key():
        return
    if not _api_key_is_configured(x_openri_api_key):
        raise HTTPException(status_code=401, detail={"error": "api_key_required"})


def _identity_hash(value: str) -> str:
    parts = [hash((salt, value)) & ((1 << 64) - 1) for salt in RATE_LIMIT_IDENTITY_SALTS]
    return "".join(f"{part:016x}" for part in parts)


def _rate_limit_identity(request: Request, x_openri_api_key: Optional[str]) -> str:
    if rate_limit_key_source() == "api_key" and require_api_key() and _api_key_is_configured(x_openri_api_key):
        return "api_key:" + _identity_hash(x_openri_api_key)
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if trust_forwarded_for() and forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip() or "unknown"
        return "forwarded:" + _identity_hash(first_hop)
    client_host = request.client.host if request.client else "unknown"
    return "client:" + _identity_hash(client_host)


def _rate_limit(request: Request, x_openri_api_key: Optional[str] = Header(default=None)) -> None:
    limit = rate_limit_per_minute()
    if limit <= 0:
        return
    client = _rate_limit_identity(request, x_openri_api_key)
    now = time.time()
    window_start = now - 60
    for key, timestamps in list(RATE_BUCKETS.items()):
        active = [ts for ts in timestamps if ts >= window_start]
        if active:
            RATE_BUCKETS[key] = active
        else:
            RATE_BUCKETS.pop(key, None)
    bucket = list(RATE_BUCKETS.get(client, []))
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail={"error": "rate_limited", "limit_per_minute": limit})
    bucket.append(now)
    RATE_BUCKETS[client] = bucket


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "openri", "version": __version__}


@app.get("/api/purpose")
def purpose() -> dict:
    return {
        "name": "Open Research Integrity",
        "short_name": "OpenRI",
        "objective": OBJECTIVE,
        "primary_workflow": "submitted_manuscript_triage_before_peer_review",
        "principles": [
            "GPT-5.5、GPT-6.7、Claude、ローカルモデルなど、モデル名や世代が変わるAI reviewer/AI editorへ同じ証拠パケットを渡す",
            "著者名、所属、評判、流行テーマによる好意的な閾値変更を入れない",
            "統計、透明性、引用、再現性、AI safetyを独立したcheckとして追加できる設計にする",
            "Web UIとAPIの両方から同じreport JSONを取得できるようにする",
            "OpenRI自体は採否エンジンにならず、自律AI判断のpreflight/evidence/accountability layerとして扱う",
        ],
    }


@app.get("/api/ai-review-protocol")
def ai_review_protocol() -> dict:
    return get_ai_review_protocol_blueprint()


@app.get("/api/submission-workflow")
def submission_workflow() -> dict:
    return {
        "name": "Submitted manuscript processing workflow",
        "purpose": "提出済み論文をAI reviewer/AI editorへ渡す前に、機械検査、証拠パケット、coverage blocker、モデル非依存の査読プロトコルを作成する。",
        "stages": [
            "提出受付: 元ファイルを保持し、検査用コピーを作成する",
            "本文/PDF抽出: PDF/TXT/TeXから本文を抽出し、PDF不可視テキストも確認する",
            "機械検査: 統計、透明性、引用、prompt injection、ruleset、PDF hidden textを実行する",
            "AI査読プロトコル化: モデル名や世代に依存しない分野非依存軸、忖度なしpolicy、coverage blockerを作成する",
            "AI判断トリアージ: 保留、統計確認、技術チェック、AI査読継続可否のいずれかに振り分ける",
            "ガードレールパケット: finding/evidence/recommendation/AI reviewer assignment/model-agnostic contractをAI editorへ渡す",
        ],
        "non_goals": [
            "不正の自動断定",
            "採否の自動決定",
            "未公開原稿の外部LLM送信を既定にすること",
        ],
    }


@app.get("/api/checks")
def checks() -> list[dict]:
    return [definition.model_dump() for definition in get_check_definitions()]


@app.post("/api/runs", response_model=RunReport, dependencies=[Depends(_require_api_key), Depends(_rate_limit)])
def run_checks(request: RunRequest) -> RunReport:
    STORE.prune_reports(retention_days())
    report = analyze_manuscript(request)
    STORE.save(report)
    return report


@app.post("/api/submissions", dependencies=[Depends(_require_api_key), Depends(_rate_limit)])
def create_submission(payload: dict = Body(...)) -> dict:
    request = RunRequest.model_validate(payload.get("run_request", payload))
    report = analyze_manuscript(request)
    STORE.save(report)
    route = report.submission_processing["recommended_route"]
    author_query = _author_query_draft(report)
    submission_id = payload.get("submission_id") or f"sub_{uuid4().hex[:12]}"
    try:
        submission = STORE.create_submission(
            {
                "submission_id": submission_id,
                "title": request.title,
                "status": "editorial_hold" if route.endswith("hold_before_peer_review") else "queued_for_editor_check",
                "recommended_route": route,
                "report_id": report.report_id,
                "author_query_draft": author_query,
            }
        )
    except SubmissionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "submission_id_conflict", "submission_id": submission_id},
        ) from exc
    submission["report"] = report.model_dump(mode="json")
    return submission


@app.get("/api/submissions", dependencies=[Depends(_require_api_key)])
def list_submissions(limit: int = 50) -> list[dict]:
    return STORE.list_submissions(limit=limit)


@app.post("/api/submissions/{submission_id}/status", dependencies=[Depends(_require_api_key)])
def update_submission_status(submission_id: str, payload: SubmissionStatusUpdate = Body(...)) -> dict:
    updated = STORE.update_submission_status(submission_id, payload.status, actor=payload.actor)
    if updated is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return updated


def _author_query_draft(report: RunReport) -> str:
    actions = report.submission_processing.get("human_actions") or []
    if not actions:
        return "現時点で著者照会が必要な重大findingはありません。coverage blockerが残る場合は追加資料の提出可否を確認してください。"
    lines = [
        "OpenRIの機械検査で、以下の点について確認が必要です。不正の断定ではなく、AI判断前に証拠をそろえるための照会です。",
    ]
    for action in actions[:5]:
        lines.append(f"- {action['check_id']}: {action['action']}")
    return "\n".join(lines)


@app.post("/api/runs/upload", response_model=RunReport, dependencies=[Depends(_require_api_key), Depends(_rate_limit)])
async def run_uploaded_file(request: Request) -> RunReport:
    STORE.prune_reports(retention_days())
    form, file = await _read_upload_form(request)
    strictness = _form_text(form, "strictness", "standard")
    review_mode = _form_text(form, "review_mode", "ai_reviewer_replication")
    activated_rulesets = _form_text(form, "activated_rulesets", "")
    enable_network = _form_bool(form, "enable_network", False)
    if strictness not in {"lenient", "standard", "strict"}:
        raise HTTPException(status_code=422, detail={"error": "invalid_strictness", "value": strictness})
    if review_mode not in {"integrity_triage", "ai_reviewer_replication"}:
        raise HTTPException(status_code=422, detail={"error": "invalid_review_mode", "value": review_mode})
    filename = _sanitize_filename(file.filename)
    limit = upload_limit_bytes()
    payload = await _read_upload_payload(file, limit)
    suffix = _validate_upload(filename, file.content_type, payload)

    pdf_inspection = None
    image_inspection = None
    source_metadata = {
        "filename": filename,
        "content_type": file.content_type,
        "size_bytes": len(payload),
        "suffix": suffix,
    }
    if suffix == ".pdf":
        # Windows cannot reopen a NamedTemporaryFile while it is still open,
        # so close the handle before passing the path to pdfplumber/pypdf.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(payload)
            pdf_path = Path(handle.name)
        try:
            try:
                text = await run_in_threadpool(extract_text_from_pdf, pdf_path)
                source_metadata["text_extraction"] = {"available": True, "method": "pdf"}
            except PDFDependencyUnavailableError as exc:
                source_metadata["text_extraction"] = {"available": False, "reason": str(exc)[:240]}
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "pdf_extraction_unavailable",
                        "message": "PDF text extraction requires optional PDF dependencies.",
                        "install": "pip install 'openri[pdf]'",
                        "source_metadata": source_metadata,
                    },
                ) from exc
            except PDFTextExtractionError as exc:
                source_metadata["text_extraction"] = {"available": False, "reason": str(exc)[:240]}
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "pdf_text_extraction_failed",
                        "message": "PDF text extraction failed; please re-upload a readable PDF or submit extracted text.",
                        "source_metadata": source_metadata,
                    },
                ) from exc
            try:
                pdf_inspection = await run_in_threadpool(inspect_pdf, pdf_path)
            except Exception as exc:  # noqa: BLE001 - report and keep the main text checks running
                pdf_inspection = {
                    "available": False,
                    "reason": str(exc),
                    "hidden_text": [],
                    "document_risks": [],
                    "page_count": 0,
                }
        finally:
            pdf_path.unlink(missing_ok=True)
    elif is_supported_image(Path(filename)):
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(payload)
            image_path = Path(handle.name)
        try:
            image_inspection = await run_in_threadpool(inspect_image, image_path)
        finally:
            image_path.unlink(missing_ok=True)
        text = (
            f"Image-only submission: {filename}\n\n"
            "The uploaded figure file was inspected for image-integrity metadata, compression, and repeated pixel-region candidates."
        )
    else:
        text = payload.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable manuscript text was found in the uploaded file.")

    rulesets = [item.strip() for item in activated_rulesets.replace(",", " ").split() if item.strip()]
    run_request = RunRequest(
        manuscript_text=text,
        title=filename,
        strictness=strictness,  # type: ignore[arg-type]
        review_mode=review_mode,  # type: ignore[arg-type]
        activated_rulesets=rulesets,
        enable_network=enable_network,
        pdf_inspection=pdf_inspection,
        image_inspection=image_inspection,
        source_metadata=source_metadata,
    )
    report = await run_in_threadpool(analyze_manuscript, run_request)
    STORE.save(report)
    return report


@app.get("/api/reports", dependencies=[Depends(_require_api_key)])
def list_reports() -> list[dict]:
    return STORE.list_recent(limit=200)


@app.get("/api/reports/{report_id}", response_model=RunReport, dependencies=[Depends(_require_api_key)])
def get_report(report_id: str) -> RunReport:
    report = STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/reports/{report_id}/sarif", dependencies=[Depends(_require_api_key)])
def get_report_sarif(report_id: str) -> dict:
    report = STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_to_sarif(report, artifact_uri=report.title)


@app.delete("/api/reports/{report_id}", dependencies=[Depends(_require_api_key)])
def delete_report(report_id: str) -> dict:
    deleted = STORE.delete(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": True, "report_id": report_id}


@app.get("/api/security-policy")
def security_policy() -> dict:
    return {
        "local_default": {
            "requires_api_key": require_api_key(),
            "network_checks_default": "disabled",
            "external_llm_default": "disabled",
        },
        "hosted_controls": {
            "api_key_header": "X-OpenRI-API-Key",
            "rate_limit_per_minute": rate_limit_per_minute(),
            "rate_limit_key": rate_limit_key_source(),
            "rate_limit_api_key_requires_auth": True,
            "trust_x_forwarded_for": trust_forwarded_for(),
            "retention_days": retention_days(),
            "cors_origins": allowed_cors_origins(),
            "cors_allow_credentials": cors_allow_credentials(),
            "rbac_boundary": "Use gateway/OIDC roles for multi-tenant deployments; built-in API key mode is single-tenant.",
        },
        "audit_policy": "Submission queue entries persist status-change audit_log records. Gateway logs should record authenticated report access.",
    }
