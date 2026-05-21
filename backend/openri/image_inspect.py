from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES


def _block_digest(image: Any, box: tuple[int, int, int, int]) -> str:
    block = image.crop(box).resize((16, 16))
    return hashlib.sha1(block.tobytes()).hexdigest()


def _duplicate_blocks(image: Any, cols: int = 4, rows: int = 4) -> list[dict]:
    width, height = image.size
    if width < cols * 8 or height < rows * 8:
        return []
    grayscale = image.convert("L")
    seen: dict[str, dict] = {}
    duplicates: list[dict] = []
    for row in range(rows):
        for col in range(cols):
            left = int(width * col / cols)
            upper = int(height * row / rows)
            right = int(width * (col + 1) / cols)
            lower = int(height * (row + 1) / rows)
            block = grayscale.crop((left, upper, right, lower))
            extrema = block.getextrema()
            if extrema[0] == extrema[1]:
                continue
            digest = _block_digest(grayscale, (left, upper, right, lower))
            current = {"row": row, "col": col, "box": [left, upper, right, lower]}
            if digest in seen:
                duplicates.append(
                    {
                        "kind": "duplicate-region-candidate",
                        "severity": "medium",
                        "first": seen[digest],
                        "second": current,
                    }
                )
            else:
                seen[digest] = current
    return duplicates


def inspect_image(path: Path) -> dict:
    try:
        from PIL import Image, UnidentifiedImageError  # type: ignore
    except ImportError:
        return {
            "available": False,
            "reason": "pillow-not-installed",
            "findings": [],
            "image_count": 0,
        }

    try:
        with Image.open(path) as image:
            image.load()
            exif = image.getexif()
            rgb = image.convert("RGB")
            duplicates = _duplicate_blocks(rgb)
            findings = list(duplicates)
            if image.format in {"JPEG", "WEBP"}:
                findings.append(
                    {
                        "kind": "lossy-compression-review",
                        "severity": "low",
                        "format": image.format,
                        "message": "lossy format; review compression history if image manipulation is suspected",
                    }
                )
            metadata = {
                "filename": path.name,
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "exif_tag_count": len(exif or {}),
            }
    except (OSError, UnidentifiedImageError) as exc:
        return {
            "available": False,
            "reason": f"image-open-failed: {str(exc)[:120]}",
            "findings": [],
            "image_count": 0,
        }

    return {
        "available": True,
        "image_count": 1,
        "metadata": metadata,
        "findings": findings,
        "analysis": {
            "duplicate_grid": "4x4",
            "exif_checked": True,
            "pixel_region_similarity": "sha1 hash of normalized 16x16 grid blocks",
            "verdict_policy": "reviewer task only; not a misconduct determination",
        },
    }
