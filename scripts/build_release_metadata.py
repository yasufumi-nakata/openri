from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()
    dist = Path(args.dist)
    out = Path(args.out)
    artifacts = []
    checksums = []
    for path in sorted(dist.glob("*")):
        if not path.is_file() or path.name.endswith((".sha256", ".spdx.json")):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {path.name}")
        artifacts.append({"fileName": path.name, "checksums": [{"algorithm": "SHA256", "checksumValue": digest}]})
    (out / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "openri-release-artifacts",
        "documentNamespace": "https://github.com/yasufumi-nakata/openri/release-artifacts",
        "creationInfo": {"creators": ["Tool: OpenRI release metadata script"]},
        "packages": artifacts,
    }
    (out / "openri-release.spdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
