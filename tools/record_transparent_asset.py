#!/usr/bin/env python3
"""Verify the accepted transparent master and write its revision-bound receipt."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "plugins" / "agent-routekit" / "assets" / "Agent RouteKit Transparent Master 220826.png"
MANIFEST = ROOT / "plugins" / "agent-routekit" / "assets" / "Logo Generation Manifest 220826.json"
RECEIPT = ROOT / "validation" / "Transparent Asset Extraction Receipt 220826.json"

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def validator_module():
    spec = importlib.util.spec_from_file_location("release_validator", ROOT / "tools" / "validate_release_candidate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    validator = validator_module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    width, height, rows = validator.decode_png_rgba(MASTER)
    subject = [
        (x, y)
        for y, row in enumerate(rows)
        for x, alpha in enumerate(row[3::4])
        if alpha >= 240
    ]
    x_values, y_values = zip(*subject)
    bbox = [min(x_values), min(y_values), max(x_values), max(y_values)]
    fill = {
        "width": round((bbox[2] - bbox[0] + 1) / width, 4),
        "height": round((bbox[3] - bbox[1] + 1) / height, 4),
    }
    corners = [rows[0][3], rows[0][(width - 1) * 4 + 3], rows[height - 1][3], rows[height - 1][(width - 1) * 4 + 3]]
    status = (
        "pass"
        if corners == [0, 0, 0, 0]
        and fill["width"] >= 0.85
        and fill["height"] >= 0.65
        and validator.sha256(MASTER) == manifest["master_sha256"]
        else "fail"
    )
    receipt = {
        "schema_version": "1.0",
        "candidate": "agent-routekit 0.1.3",
        "product_revision_sha256": validator.product_revision_sha256(),
        "status": status,
        "source_classification": "deterministic_transparent_derivative",
        "opaque_parent_sha256": manifest["opaque_parent_sha256"],
        "transparent_master_sha256": validator.sha256(MASTER),
        "dimensions": [width, height],
        "corner_alpha": corners,
        "subject_bbox": bbox,
        "subject_safe_fill": fill,
        "geometry_mutation": "none_after_accepted_transparent_master",
        "publication_action": "none",
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
