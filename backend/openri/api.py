from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .analyzer import OBJECTIVE, analyze_manuscript, get_ai_review_protocol_blueprint, get_check_definitions
from .config import allowed_cors_origins, configured_api_keys, rate_limit_per_minute, require_api_key, retention_days, upload_limit_bytes
from .image_inspect import SUPPORTED_IMAGE_SUFFIXES, inspect_image, is_supported_image
from .models import RunReport, RunRequest
from .pdf import extract_text_from_pdf
from .pdf_inspect import inspect_pdf
from .sarif import report_to_sarif
from .store import ReportStore


app = FastAPI(
    title="OpenRI API",
    version=__version__,
    description="OSS research-integrity test runner for manuscripts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE = ReportStore()
RATE_BUCKETS: dict[str, list[float]] = {}


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".tex", ".rst"}
UPLOAD_SUFFIXES = TEXT_SUFFIXES | {".pdf"} | SUPPORTED_IMAGE_SUFFIXES


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
    )
    return payload.startswith(signatures)


def _validate_upload(filename: str, content_type: Optional[str], payload: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=422,
            detail={"error": "unsupported_file_type", "allowed_extensions": sorted(UPLOAD_SUFFIXES), "filename": filename},
        )
    if suffix == ".pdf" and not _looks_like_pdf(payload):
        raise HTTPException(status_code=422, detail={"error": "invalid_pdf_magic", "filename": filename})
    if suffix in SUPPORTED_IMAGE_SUFFIXES and not _looks_like_image(payload):
        raise HTTPException(status_code=422, detail={"error": "invalid_image_magic", "filename": filename})
    if suffix in TEXT_SUFFIXES and content_type and content_type not in {
        "text/plain",
        "text/markdown",
        "text/x-tex",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=422, detail={"error": "invalid_text_content_type", "content_type": content_type})
    return suffix


async def _read_upload_form(request: Request):
    try:
        form = await request.form()
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


def _require_api_key(x_openri_api_key: Optional[str] = Header(default=None)) -> None:
    if not require_api_key():
        return
    keys = configured_api_keys()
    if not keys or x_openri_api_key not in keys:
        raise HTTPException(status_code=401, detail={"error": "api_key_required"})


def _rate_limit(request: Request) -> None:
    limit = rate_limit_per_minute()
    if limit <= 0:
        return
    client = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60
    bucket = [ts for ts in RATE_BUCKETS.get(client, []) if ts >= window_start]
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
            "人間査読で確認される論点を、Codex/Claude等のAI reviewerが証拠優先で再現できるテスト設計にする",
            "著者名、所属、評判、流行テーマによる好意的な閾値変更を入れない",
            "統計、透明性、引用、再現性、AI safetyを独立したcheckとして追加できる設計にする",
            "Web UIとAPIの両方から同じreport JSONを取得できるようにする",
            "不正断定や採否自動決定ではなく、査読前/査読中に潰すべき再現可能な検査結果として扱う",
        ],
    }


@app.get("/api/ai-review-protocol")
def ai_review_protocol() -> dict:
    return get_ai_review_protocol_blueprint()


@app.get("/api/submission-workflow")
def submission_workflow() -> dict:
    return {
        "name": "Submitted manuscript processing workflow",
        "purpose": "提出済み論文を通常査読またはAI査読へ回す前に、編集部側で機械検査と査読プロトコル作成を行う。",
        "stages": [
            "提出受付: 元ファイルを保持し、検査用コピーを作成する",
            "本文/PDF抽出: PDF/TXT/TeXから本文を抽出し、PDF不可視テキストも確認する",
            "機械検査: 統計、透明性、引用、prompt injection、ruleset、PDF hidden textを実行する",
            "AI査読プロトコル化: Codex/Claude等が見るべき分野非依存軸、忖度なしpolicy、coverage blockerを作成する",
            "編集部トリアージ: 保留、統計確認、技術チェック、AI査読/通常査読のいずれかに振り分ける",
            "確認パケット: finding/evidence/recommendation/AI reviewer assignmentをhandling editorへ渡す",
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
    submission = STORE.create_submission(
        {
            "submission_id": payload.get("submission_id") or f"sub_{uuid4().hex[:12]}",
            "title": request.title,
            "status": "editorial_hold" if route.endswith("hold_before_peer_review") else "queued_for_editor_check",
            "recommended_route": route,
            "report_id": report.report_id,
            "author_query_draft": author_query,
        }
    )
    submission["report"] = report.model_dump(mode="json")
    return submission


@app.get("/api/submissions", dependencies=[Depends(_require_api_key)])
def list_submissions(limit: int = 50) -> list[dict]:
    return STORE.list_submissions(limit=limit)


@app.post("/api/submissions/{submission_id}/status", dependencies=[Depends(_require_api_key)])
def update_submission_status(submission_id: str, payload: dict = Body(...)) -> dict:
    status = str(payload.get("status", "")).strip()
    if not status:
        raise HTTPException(status_code=422, detail={"error": "status_required"})
    updated = STORE.update_submission_status(submission_id, status, actor=str(payload.get("actor", "openri")))
    if updated is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return updated


def _author_query_draft(report: RunReport) -> str:
    actions = report.submission_processing.get("human_actions") or []
    if not actions:
        return "現時点で著者照会が必要な重大findingはありません。coverage blockerが残る場合は追加資料の提出可否を確認してください。"
    lines = [
        "OpenRIの機械検査で、以下の点について確認が必要です。不正の断定ではなく、査読前に証拠をそろえるための照会です。",
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
    payload = await file.read()
    limit = upload_limit_bytes()
    if len(payload) > limit:
        raise HTTPException(status_code=413, detail={"error": "file_too_large", "limit_bytes": limit})
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
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as handle:
            handle.write(payload)
            handle.flush()
            pdf_path = Path(handle.name)
            text = extract_text_from_pdf(pdf_path)
            try:
                pdf_inspection = inspect_pdf(pdf_path)
            except Exception as exc:  # noqa: BLE001 - report and keep the main text checks running
                pdf_inspection = {"available": False, "reason": str(exc), "hidden_text": [], "document_risks": [], "page_count": 0}
    elif is_supported_image(Path(filename)):
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as handle:
            handle.write(payload)
            handle.flush()
            image_inspection = inspect_image(Path(handle.name))
        text = (
            f"Image-only submission: {filename}\n\n"
            "The uploaded figure file was inspected for image-integrity metadata, compression, and repeated pixel-region candidates."
        )
    else:
        text = payload.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable manuscript text was found in the uploaded file.")

    rulesets = [item.strip() for item in activated_rulesets.replace(",", " ").split() if item.strip()]
    report = analyze_manuscript(
        RunRequest(
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
    )
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
            "retention_days": retention_days(),
            "cors_origins": allowed_cors_origins(),
            "rbac_boundary": "Use gateway/OIDC roles for multi-tenant deployments; built-in API key mode is single-tenant.",
        },
        "audit_policy": "Submission queue entries persist status-change audit_log records. Gateway logs should record authenticated report access.",
    }
