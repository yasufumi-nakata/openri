from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from .models import RunReport


def default_db_path() -> Path:
    env = os.environ.get("OPENRI_DB_PATH")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".openri" / "reports.sqlite3"


class ReportStore:
    def __init__(self, path: Path | None = None):
        self.path = path or default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    strictness TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    warnings INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recommended_route TEXT NOT NULL,
                    report_id TEXT,
                    author_query_draft TEXT NOT NULL,
                    audit_log TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, report: RunReport) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reports
                (report_id, title, created_at, strictness, score, failed, warnings, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_id,
                    report.title,
                    report.created_at.isoformat(),
                    report.strictness,
                    report.summary.score,
                    report.summary.failed,
                    report.summary.warnings,
                    report.model_dump_json(),
                ),
            )
            conn.commit()

    def get(self, report_id: str) -> Optional[RunReport]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT payload FROM reports WHERE report_id = ?", (report_id,)
            ).fetchone()
        if row is None:
            return None
        return RunReport.model_validate_json(row["payload"])

    def list_recent(self, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT report_id, title, created_at, score, failed, warnings "
                "FROM reports ORDER BY datetime(created_at) DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, report_id: str) -> bool:
        with closing(self._connect()) as conn:
            cursor = conn.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0

    def prune_reports(self, older_than_days: int) -> int:
        if older_than_days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            cursor = conn.execute("DELETE FROM reports WHERE datetime(created_at) < datetime(?)", (cutoff_iso,))
            conn.commit()
            return cursor.rowcount

    def create_submission(self, submission: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        audit_log = submission.get("audit_log") or [
            {"at": now, "event": "created", "actor": "openri", "status": submission["status"]}
        ]
        payload = {
            "submission_id": submission["submission_id"],
            "title": submission["title"],
            "status": submission["status"],
            "recommended_route": submission["recommended_route"],
            "report_id": submission.get("report_id"),
            "author_query_draft": submission.get("author_query_draft", ""),
            "audit_log": audit_log,
            "created_at": now,
            "updated_at": now,
        }
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO submissions
                (submission_id, title, status, recommended_route, report_id, author_query_draft, audit_log, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["submission_id"],
                    payload["title"],
                    payload["status"],
                    payload["recommended_route"],
                    payload["report_id"],
                    payload["author_query_draft"],
                    json.dumps(payload["audit_log"], ensure_ascii=False),
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
            conn.commit()
        return payload

    def list_submissions(self, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT submission_id, title, status, recommended_route, report_id, author_query_draft,
                       audit_log, created_at, updated_at
                FROM submissions ORDER BY datetime(updated_at) DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["audit_log"] = json.loads(item["audit_log"])
            out.append(item)
        return out

    def update_submission_status(self, submission_id: str, status: str, actor: str = "openri") -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM submissions WHERE submission_id = ?", (submission_id,)).fetchone()
            if row is None:
                return None
            item = dict(row)
            audit_log = json.loads(item["audit_log"])
            now = datetime.now(timezone.utc).isoformat()
            audit_log.append({"at": now, "event": "status_updated", "actor": actor, "status": status})
            conn.execute(
                "UPDATE submissions SET status = ?, audit_log = ?, updated_at = ? WHERE submission_id = ?",
                (status, json.dumps(audit_log, ensure_ascii=False), now, submission_id),
            )
            conn.commit()
        item["status"] = status
        item["audit_log"] = audit_log
        item["updated_at"] = now
        return item
