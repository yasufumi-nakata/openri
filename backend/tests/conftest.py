from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / "openri-pytest-reports.sqlite3"
os.environ.setdefault("OPENRI_DB_PATH", str(TEST_DB_PATH))

try:
    TEST_DB_PATH.unlink()
except FileNotFoundError:
    pass
