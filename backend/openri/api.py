from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .analyzer import OBJECTIVE, analyze_manuscript, get_ai_review_protocol_blueprint, get_check_definitions
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE = ReportStore()


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


@app.post("/api/runs", response_model=RunReport)
def run_checks(request: RunRequest) -> RunReport:
    report = analyze_manuscript(request)
    STORE.save(report)
    return report


@app.post("/api/runs/upload", response_model=RunReport)
async def run_uploaded_file(
    file: UploadFile = File(...),
    strictness: str = Form("standard"),
    review_mode: str = Form("ai_reviewer_replication"),
    activated_rulesets: str = Form(""),
    enable_network: bool = Form(False),
) -> RunReport:
    suffix = Path(file.filename or "manuscript.txt").suffix.lower()
    payload = await file.read()
    if len(payload) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is too large for the prototype limit.")

    pdf_inspection = None
    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as handle:
            handle.write(payload)
            handle.flush()
            pdf_path = Path(handle.name)
            text = extract_text_from_pdf(pdf_path)
            try:
                pdf_inspection = inspect_pdf(pdf_path)
            except Exception as exc:  # noqa: BLE001 - report and keep the main text checks running
                pdf_inspection = {"available": False, "reason": str(exc), "hidden_text": [], "page_count": 0}
    else:
        text = payload.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable manuscript text was found in the uploaded file.")

    rulesets = [item.strip() for item in activated_rulesets.replace(",", " ").split() if item.strip()]
    report = analyze_manuscript(
        RunRequest(
            manuscript_text=text,
            title=file.filename or "Uploaded manuscript",
            strictness=strictness,  # type: ignore[arg-type]
            review_mode=review_mode,  # type: ignore[arg-type]
            activated_rulesets=rulesets,
            enable_network=enable_network,
            pdf_inspection=pdf_inspection,
        )
    )
    STORE.save(report)
    return report


@app.get("/api/reports")
def list_reports() -> list[dict]:
    return STORE.list_recent(limit=200)


@app.get("/api/reports/{report_id}", response_model=RunReport)
def get_report(report_id: str) -> RunReport:
    report = STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/reports/{report_id}/sarif")
def get_report_sarif(report_id: str) -> dict:
    report = STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_to_sarif(report, artifact_uri=report.title)
