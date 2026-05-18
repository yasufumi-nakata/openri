from __future__ import annotations

import json
from pathlib import Path

from openri.models import RunReport, SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    schema = RunReport.model_json_schema()
    schema["$id"] = f"https://github.com/yasufumi-nakata/openri/schemas/{SCHEMA_VERSION}.schema.json"
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "OpenRI RunReport"
    out = ROOT / "schemas" / f"{SCHEMA_VERSION}.schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
