from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
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
