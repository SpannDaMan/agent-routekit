#!/usr/bin/env python3
"""Validate the standalone Agent RouteKit release candidate with stdlib only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "agent-routekit"

REQUIRED_FILES = (
    ".gitignore",
    "LICENSE",
    "README.md",
    "BRAND.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DESIGN.md",
    "design.tokens.json",
    "MAINTAINER-PILOT.md",
    "PROVENANCE.md",
    "PRIVACY.md",
    "PUBLICATION-GATE.md",
    "RELEASE-CHECKLIST.md",
    "SECURITY.md",
    "SUPPORT.md",
    "TERMS.md",
    "THREAT-MODEL.md",
    "pyproject.toml",
    "tests/test_release_validator.py",
    "tests/test_routekit.py",
    "tests/test_activation_golden.py",
    "tools/demo.py",
    "tools/validate_release_candidate.py",
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".github/FUNDING.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/test.yml",
    "docs/CODEX-INSTALL.md",
    "docs/CLAUDE-INSTALL.md",
    "docs/EVALUATION.md",
    "docs/OPENAI-PLUGIN-SUBMISSION.md",
    "docs/RECEIPTS.md",
    "docs/RELEASE-EVIDENCE.md",
    "docs/ROUTING-CONTRACT.md",
    "plugins/agent-routekit/.codex-plugin/plugin.json",
    "plugins/agent-routekit/.claude-plugin/plugin.json",
    "plugins/agent-routekit/routes.example.json",
    "plugins/agent-routekit/registry.schema.json",
    "plugins/agent-routekit/task.schema.json",
    "plugins/agent-routekit/receipt.schema.json",
    "plugins/agent-routekit/outcome.schema.json",
    "plugins/agent-routekit/scripts/routekit.py",
    "plugins/agent-routekit/skills/agent-routekit/SKILL.md",
    "plugins/agent-routekit/examples/routine-task.json",
    "plugins/agent-routekit/examples/high-risk-task.json",
    "examples/outcome-attachment-template.json",
    "examples/outcome-case-template.json",
    "evidence/outcome-case-manifest.json",
    "plugins/agent-routekit/assets/sample-receipt.json",
    "plugins/agent-routekit/assets/Agent RouteKit Transparent Master 220826.png",
    "plugins/agent-routekit/assets/Logo Generation Manifest 220826.json",
    "plugins/agent-routekit/assets/icon.png",
    "plugins/agent-routekit/assets/logo.png",
    "plugins/agent-routekit/assets/logo-dark.png",
    "plugins/agent-routekit/assets/screenshot1.png",
    "plugins/agent-routekit/assets/social-preview.png",
    "evals/agent-routekit-suite.json",
    "evals/agent-routekit-activation-golden.json",
    "submission/openai-plugin-submission.json",
    "tools/run_evals.py",
    "tools/record_transparent_asset.py",
    "tools/validate_provider_packages.py",
    "tools/validate_activation_golden.py",
    "tools/validate_outcome_case.py",
)

EXPECTED_PNGS = {
    "plugins/agent-routekit/assets/Agent RouteKit Transparent Master 220826.png": (1254, 1254, True),
    "plugins/agent-routekit/assets/icon.png": (512, 512, True),
    "plugins/agent-routekit/assets/logo.png": (1024, 1024, False),
    "plugins/agent-routekit/assets/logo-dark.png": (1024, 1024, False),
    "plugins/agent-routekit/assets/screenshot1.png": (1600, 900, False),
    "plugins/agent-routekit/assets/social-preview.png": (1600, 900, False),
}

PRIVATE_MARKERS = (
    "agent" + " smith projects",
    "agent" + "-smith-task-force",
    "diggy" + " digital",
    "markeys" + " meta ad specialist",
    "mr" + " krabs",
    "app" + "ollonia",
    "show" + "time",
    "slack" + "-agent-hub",
    "obsidian" + " brains",
    "runtime" + "/astf/",
    "chatgpt" + "-web-browser-lane",
    "agent" + " smith",
    "ai" + " agents project",
    "conversation" + "_url",
    "container" + "_service",
    "browser" + "_content_id",
    "lease" + "_status",
    "generation" + "_lane",
)

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{16,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+", re.IGNORECASE),
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
)

TEXT_SUFFIXES = {".md", ".json", ".py", ".toml", ".yml", ".yaml", ".ps1", ".svg"}
TEXT_REVISION_SUFFIXES = {".json", ".md", ".py", ".ps1", ".svg", ".toml", ".txt", ".yml", ".yaml"}
MAX_FILE_BYTES = 1_000_000
EXCLUDED_REVISION_PARTS = {"validation", ".git", "build", "dist", "__pycache__"}
GENERATED_RESIDUE_PARTS = {"build", "dist", "__pycache__"}
EXCLUDED_SCAN_PARTS = {".git"}
REQUIRED_EVIDENCE = (
    "validation/Transparent Asset Extraction Receipt 220826.json",
    "validation/Agent RouteKit Eval Result 220826.json",
    "validation/Codex Plugin Verification 220826.json",
    "validation/Claude Plugin Verification 220826.json",
)


def load_json(path: Path) -> Any:
    """Load one UTF-8 JSON artifact from the candidate."""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for an asset."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def product_revision_sha256() -> str:
    """Return the non-self-referential digest for candidate product bytes."""

    records: list[str] = []
    for path in sorted(ROOT.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_REVISION_PARTS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if not path.is_file() or path.is_symlink() or path.suffix == ".pyc":
            continue
        data = path.read_bytes()
        if path.suffix.casefold() in TEXT_REVISION_SUFFIXES or path.name == "LICENSE":
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        records.append(f"{relative.as_posix()}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\n")
    return hashlib.sha256("".join(records).encode("utf-8")).hexdigest()


def paeth(left: int, up: int, upper_left: int) -> int:
    """Return the PNG Paeth predictor value for three neighboring bytes."""

    estimate = left + up - upper_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
    return (left, up, upper_left)[distances.index(min(distances))]


def decode_png_rgba(path: Path) -> tuple[int, int, list[bytes]]:
    """Decode a non-interlaced 8-bit RGBA PNG using only the standard library."""

    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")

    offset = 8
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break

    if None in (width, height, bit_depth, color_type, interlace):
        raise ValueError("missing IHDR")
    if bit_depth != 8 or color_type not in {2, 6} or interlace != 0:
        raise ValueError(f"expected non-interlaced 8-bit RGB/RGBA, got depth={bit_depth} type={color_type} interlace={interlace}")

    raw = zlib.decompress(bytes(compressed))
    bytes_per_pixel = 3 if color_type == 2 else 4
    stride = width * bytes_per_pixel
    rows: list[bytes] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        source = raw[cursor : cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = value + left
            elif filter_type == 2:
                decoded = value + up
            elif filter_type == 3:
                decoded = value + ((left + up) // 2)
            elif filter_type == 4:
                decoded = value + paeth(left, up, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            row[index] = decoded & 0xFF
        if color_type == 2:
            rgba = bytearray(width * 4)
            for pixel in range(width):
                rgb_offset = pixel * 3
                rgba_offset = pixel * 4
                rgba[rgba_offset : rgba_offset + 3] = row[rgb_offset : rgb_offset + 3]
                rgba[rgba_offset + 3] = 255
            rows.append(bytes(rgba))
        else:
            rows.append(bytes(row))
        previous = row
    return width, height, rows


def validate_png(path: Path, expected: tuple[int, int, bool]) -> list[str]:
    """Validate PNG dimensions, corner alpha, and transparent-mark coverage."""

    errors: list[str] = []
    try:
        width, height, rows = decode_png_rgba(path)
    except (OSError, ValueError, zlib.error, struct.error) as exc:
        return [f"{path.relative_to(ROOT)}: PNG decode failed: {exc}"]

    expected_width, expected_height, transparent = expected
    if (width, height) != (expected_width, expected_height):
        errors.append(
            f"{path.relative_to(ROOT)}: expected {expected_width}x{expected_height}, got {width}x{height}"
        )

    corners = (
        rows[0][3],
        rows[0][(width - 1) * 4 + 3],
        rows[height - 1][3],
        rows[height - 1][(width - 1) * 4 + 3],
    )
    if transparent and any(alpha != 0 for alpha in corners):
        errors.append(f"{path.relative_to(ROOT)}: transparent asset corners are not fully transparent")
    if not transparent and any(alpha != 255 for alpha in corners):
        errors.append(f"{path.relative_to(ROOT)}: opaque asset corners are not fully opaque")

    if transparent:
        subject_points = [
            (x, y)
            for y, row in enumerate(rows)
            for x, alpha in enumerate(row[3::4])
            if alpha >= 240
        ]
        opaque_pixels = len(subject_points)
        coverage = opaque_pixels / (width * height)
        if not 0.05 <= coverage <= 0.55:
            errors.append(f"{path.relative_to(ROOT)}: subject coverage {coverage:.3f} is outside 0.05–0.55")
        if subject_points:
            x_values, y_values = zip(*subject_points)
            width_fill = (max(x_values) - min(x_values) + 1) / width
            height_fill = (max(y_values) - min(y_values) + 1) / height
            if width_fill < 0.85 or height_fill < 0.65:
                errors.append(
                    f"{path.relative_to(ROOT)}: transparent subject safe fill {width_fill:.3f}×{height_fill:.3f} is too small"
                )
        else:
            errors.append(f"{path.relative_to(ROOT)}: transparent asset has no visible subject")
    return errors


def validate_file_shape() -> list[str]:
    """Reject symlinks, generated bytecode, and oversized candidate files."""

    errors: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_SCAN_PARTS for part in relative.parts):
            continue
        if any(part in GENERATED_RESIDUE_PARTS or part.endswith(".egg-info") for part in relative.parts):
            errors.append(f"generated residue is not allowed: {relative}")
            continue
        if path.is_symlink():
            errors.append(f"symlink is not allowed: {relative}")
            continue
        if not path.is_file():
            continue
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            errors.append(f"generated Python cache is not allowed: {relative}")
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"file exceeds {MAX_FILE_BYTES} bytes: {relative}")
    return errors


def validate_text_safety() -> list[str]:
    """Scan public text artifacts for secrets, private markers, paths, and placeholders."""

    errors: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_SCAN_PARTS for part in relative.parts):
            continue
        if not path.is_file() or (path.suffix.lower() not in TEXT_SUFFIXES and path.name != "LICENSE"):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        lower = text.lower()
        for marker in PRIVATE_MARKERS:
            if marker in lower:
                errors.append(f"private marker {marker!r} found in {relative}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"secret-like value matched {pattern.pattern!r} in {relative}")
        for pattern in ABSOLUTE_PATH_PATTERNS:
            if pattern.search(text):
                errors.append(f"absolute user path matched {pattern.pattern!r} in {relative}")
        placeholder_markers = ("[" + "todo:", "[" + "todo]")
        if any(marker in lower for marker in placeholder_markers):
            errors.append(f"TODO placeholder found in {relative}")
    return errors


def validate_metadata() -> list[str]:
    """Validate plugin, marketplace, asset-reference, and license metadata."""

    errors: list[str] = []
    manifest_path = PLUGIN / ".codex-plugin" / "plugin.json"
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    try:
        manifest = load_json(manifest_path)
        marketplace = load_json(marketplace_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"metadata JSON failed: {exc}"]
    if not isinstance(manifest, dict):
        return ["plugin.json must contain a JSON object"]
    if not isinstance(marketplace, dict):
        return ["marketplace.json must contain a JSON object"]

    expected_manifest = {
        "name": "agent-routekit",
        "version": "0.1.1",
        "license": "MIT",
        "homepage": "https://github.com/SpannDaMan/agent-routekit",
        "repository": "https://github.com/SpannDaMan/agent-routekit",
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            errors.append(f"plugin.json {field} must be {expected!r}")
    author = manifest.get("author", {})
    if not isinstance(author, dict) or author.get("name") != "Orbral":
        errors.append("plugin.json author.name must be Orbral")

    interface = manifest.get("interface", {})
    if not isinstance(interface, dict):
        errors.append("plugin.json interface must be an object")
        interface = {}
    expected_interface = {
        "developerName": "Orbral",
        "category": "Developer Tools",
        "shortDescription": "Plan the route, not the run.",
        "privacyPolicyURL": "https://github.com/SpannDaMan/agent-routekit/blob/main/PRIVACY.md",
        "termsOfServiceURL": "https://github.com/SpannDaMan/agent-routekit/blob/main/TERMS.md",
    }
    for field, expected in expected_interface.items():
        if interface.get(field) != expected:
            errors.append(f"plugin.json interface.{field} must be {expected!r}")
    for field in ("composerIcon", "logo", "logoDark"):
        value = interface.get(field)
        if not isinstance(value, str) or not (PLUGIN / value).is_file():
            errors.append(f"plugin.json interface.{field} must reference an existing asset")
    if "screenshots" in interface:
        errors.append("skills-only plugin must not declare interface.screenshots")

    if marketplace.get("name") != "agent-routekit":
        errors.append("marketplace name must be agent-routekit")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append("marketplace must contain exactly one plugin entry")
    else:
        entry = entries[0]
        if not isinstance(entry, dict):
            errors.append("marketplace plugin entry must be an object")
            entry = {}
        source = entry.get("source", {})
        policy = entry.get("policy", {})
        if not isinstance(source, dict):
            errors.append("marketplace plugin source must be an object")
            source = {}
        if not isinstance(policy, dict):
            errors.append("marketplace plugin policy must be an object")
            policy = {}
        if entry.get("name") != "agent-routekit":
            errors.append("marketplace plugin name must be agent-routekit")
        if source.get("path") != "./plugins/agent-routekit":
            errors.append("marketplace source path must be ./plugins/agent-routekit")
        if policy.get("installation") != "AVAILABLE":
            errors.append("marketplace installation policy must be AVAILABLE")
        if policy.get("authentication") != "ON_INSTALL":
            errors.append("marketplace authentication policy must remain ON_INSTALL until provider semantics are re-verified")

    try:
        claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
        claude_plugin = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
        submission = load_json(ROOT / "submission" / "openai-plugin-submission.json")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"provider package JSON failed: {exc}")
        claude_marketplace = claude_plugin = submission = {}
    if not isinstance(claude_marketplace, dict) or claude_marketplace.get("name") != "agent-routekit":
        errors.append("Claude marketplace name must be agent-routekit")
    if not isinstance(claude_plugin, dict) or claude_plugin.get("name") != "local-model-route-planner":
        errors.append("Claude plugin name must be local-model-route-planner")
    if isinstance(claude_plugin, dict) and claude_plugin.get("version") != manifest.get("version"):
        errors.append("Claude plugin version must match Codex plugin version")
    if not isinstance(submission, dict) or submission.get("submission_type") != "skills_only":
        errors.append("OpenAI submission must declare skills_only")
    if isinstance(submission, dict):
        if submission.get("publisher") != "Orbral":
            errors.append("OpenAI submission publisher must be Orbral")
        if submission.get("category") != "Developer Tools":
            errors.append("OpenAI submission category must be Developer Tools")
        if submission.get("plugin_name") != "Local Model Route Planner":
            errors.append("OpenAI submission plugin_name must be Local Model Route Planner")
        if submission.get("short_description") != "Plan the route, not the run.":
            errors.append("OpenAI submission short_description must match the public subtitle")
        if len(submission.get("starter_prompts", [])) != 3:
            errors.append("OpenAI submission must contain three starter prompts")
        if len(submission.get("positive_tests", [])) != 5 or len(submission.get("negative_tests", [])) != 3:
            errors.append("OpenAI submission must contain five positive and three negative cases")
        if any("mcp" in str(key).lower() for key in submission):
            errors.append("OpenAI submission must not declare an MCP package")

    try:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"LICENSE read failed: {exc}")
        return errors
    if not license_text.startswith("MIT License\n") or "Copyright (c) 2026 SpannDaMan" not in license_text:
        errors.append("LICENSE must be the approved 2026 SpannDaMan MIT license")
    return errors


def validate_json_artifacts() -> list[str]:
    """Verify that every committed JSON artifact is readable and syntactically valid."""

    errors: list[str] = []
    for relative in (
        "design.tokens.json",
        "plugins/agent-routekit/routes.example.json",
        "plugins/agent-routekit/registry.schema.json",
        "plugins/agent-routekit/task.schema.json",
        "plugins/agent-routekit/receipt.schema.json",
        "plugins/agent-routekit/outcome.schema.json",
        "plugins/agent-routekit/examples/routine-task.json",
        "plugins/agent-routekit/examples/high-risk-task.json",
        "examples/outcome-attachment-template.json",
        "examples/outcome-case-template.json",
        "evidence/outcome-case-manifest.json",
        "plugins/agent-routekit/assets/sample-receipt.json",
        "evals/agent-routekit-activation-golden.json",
        "plugins/agent-routekit/assets/Logo Generation Manifest 220826.json",
        ".claude-plugin/marketplace.json",
        "plugins/agent-routekit/.claude-plugin/plugin.json",
        "evals/agent-routekit-suite.json",
        "submission/openai-plugin-submission.json",
    ):
        try:
            load_json(ROOT / relative)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {relative}: {exc}")
    return errors


def validate_logo_provenance() -> list[str]:
    """Require the accepted transparent master and public-safe derivative custody."""

    errors: list[str] = []
    manifest_path = PLUGIN / "assets" / "Logo Generation Manifest 220826.json"
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"logo generation manifest failed: {exc}"]
    expected_relative = "plugins/agent-routekit/assets/Agent RouteKit Transparent Master 220826.png"
    master_path = ROOT / expected_relative
    if manifest.get("canonical_master") != expected_relative:
        errors.append("logo manifest canonical_master mismatch")
    if manifest.get("source_type") != "deterministic_transparent_derivative":
        errors.append("logo manifest source_type must be deterministic_transparent_derivative")
    if "GPT Image 2" not in str(manifest.get("generation_mode", "")):
        errors.append("logo manifest must record GPT Image 2 generation")
    if manifest.get("source_background_policy") != "transparent_source":
        errors.append("logo manifest source_background_policy must be transparent_source")
    if manifest.get("local_edit_status") != "background_extraction_and_safe_fill_only":
        errors.append("logo manifest must record background_extraction_and_safe_fill_only")
    if manifest.get("opaque_parent_sha256") != "01684a291239db37aaa354697cf61e445be4c0635b4831de3fc54c6113772e21":
        errors.append("logo manifest opaque_parent_sha256 mismatch")
    if manifest.get("extraction_receipt") != "validation/Transparent Asset Extraction Receipt 220826.json":
        errors.append("logo manifest extraction receipt mismatch")
    if master_path.is_file():
        actual = hashlib.sha256(master_path.read_bytes()).hexdigest()
        if actual != str(manifest.get("master_sha256", "")).casefold():
            errors.append("canonical logo master hash mismatch")
    for retired in (
        "Agent RouteKit Mini Logo 120826.png",
        "Agent RouteKit " + "Agent " + "Smith Palette Master 210826.png",
        "Agent RouteKit GPT Image 2 Master 140826.png",
        "agent-routekit-mark.svg",
    ):
        if (PLUGIN / "assets" / retired).exists():
            errors.append(f"retired local logo source still exists: {retired}")
    try:
        script = (ROOT / "tools" / "render_brand_assets.ps1").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"brand renderer read failed: {exc}")
    else:
        for required in ("Place-Master", "DrawImage", "master_sha256", "transparent_source"):
            if required not in script:
                errors.append(f"brand renderer is missing source-only control: {required}")
        for forbidden in ("Draw-RouteKitMark", "Draw-OptimizerMark", "function Draw-Mark", "function Mark(", "FillEllipse", "FillPolygon", "DrawLines", "DrawPath", "GraphicsPath"):
            if forbidden.casefold() in script.casefold():
                errors.append(f"brand renderer contains prohibited logo-origin operation: {forbidden}")
    return errors


def validate_evidence_bindings() -> list[str]:
    """Reject stale or incomplete targeted evidence for the current product revision."""

    errors: list[str] = []
    revision = product_revision_sha256()
    for relative in REQUIRED_EVIDENCE:
        path = ROOT / relative
        try:
            receipt = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"required evidence failed: {relative}: {exc}")
            continue
        if receipt.get("status") != "pass":
            errors.append(f"required evidence is not passing: {relative}")
        if receipt.get("product_revision_sha256") != revision:
            errors.append(f"stale product revision evidence: {relative}")
    return errors


def validate_sample_receipt() -> list[str]:
    """Compare the committed sample receipt with a fresh deterministic planner run."""

    output = subprocess.run(
        [
            sys.executable,
            str(PLUGIN / "scripts" / "routekit.py"),
            "plan",
            "--registry",
            str(PLUGIN / "routes.example.json"),
            "--task",
            str(PLUGIN / "examples" / "high-risk-task.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if output.returncode != 0:
        return [f"high-risk demo failed: {output.stderr.strip()}"]
    try:
        generated = json.loads(output.stdout)
        saved = load_json(PLUGIN / "assets" / "sample-receipt.json")
    except (OSError, json.JSONDecodeError) as exc:
        return [f"sample receipt JSON failed: {exc}"]
    if generated != saved:
        return ["sample-receipt.json does not match the current deterministic high-risk demo"]
    return []


def validate_demo() -> list[str]:
    """Verify the one-command demo, canonical CLI, and README output remain identical."""

    demo = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "demo.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    canonical = subprocess.run(
        [
            sys.executable,
            str(PLUGIN / "scripts" / "routekit.py"),
            "plan",
            "--registry",
            str(PLUGIN / "routes.example.json"),
            "--task",
            str(PLUGIN / "examples" / "high-risk-task.json"),
            "--format",
            "text",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    errors: list[str] = []
    if demo.returncode != 0:
        errors.append(f"one-command demo failed: {demo.stderr.strip()}")
    if canonical.returncode != 0:
        errors.append(f"canonical text demo failed: {canonical.stderr.strip()}")
    if not errors and demo.stdout != canonical.stdout:
        errors.append("tools/demo.py output does not match the canonical CLI")
    try:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read README.md for demo verification: {exc}")
    else:
        if demo.stdout.strip() not in readme:
            errors.append("README.md does not contain the exact one-command demo output")
    return errors


def validate_activation_golden() -> list[str]:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "validate_activation_golden.py"),
            "--suite",
            str(ROOT / "evals" / "agent-routekit-activation-golden.json"),
            "--product-revision",
            product_revision_sha256(),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return [] if completed.returncode == 0 else [f"activation golden suite failed: {(completed.stdout + completed.stderr).strip()[-500:]}"]


def validate_publication_outcome_gate() -> list[str]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_outcome_case.py"), "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return []
    try:
        receipt = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return ["independent outcome publication gate could not be evaluated"]
    return [f"publication hold: {receipt.get('observed_case_count', 0)}/1 host-independent decision-to-outcome cases passed"]


def validate_required_files() -> list[str]:
    """Return every missing path required by the standalone candidate."""

    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"required file is missing: {relative}")
    return errors


def validate_png_assets() -> tuple[list[str], dict[str, str]]:
    """Validate every required PNG once and return its stable digest map."""

    errors: list[str] = []
    asset_hashes: dict[str, str] = {}
    for relative, expected in EXPECTED_PNGS.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"PNG asset is missing: {relative}")
            continue
        errors.extend(validate_png(path, expected))
        try:
            asset_hashes[relative] = sha256(path)
        except OSError as exc:
            errors.append(f"cannot hash PNG asset {relative}: {exc}")
    return errors, asset_hashes


def run_validation() -> dict[str, Any]:
    """Run every release check once and return one internally consistent receipt."""

    png_errors, asset_hashes = validate_png_assets()
    check_errors = {
        "required_files": validate_required_files(),
        "portable_file_shape": validate_file_shape(),
        "text_safety": validate_text_safety(),
        "metadata": validate_metadata(),
        "json_artifacts": validate_json_artifacts(),
        "logo_provenance": validate_logo_provenance(),
        "evidence_bindings": validate_evidence_bindings(),
        "sample_receipt": validate_sample_receipt(),
        "one_command_demo": validate_demo(),
        "activation_golden": validate_activation_golden(),
        "publication_outcome_gate": validate_publication_outcome_gate(),
        "png_assets": png_errors,
    }

    errors = sorted({error for group in check_errors.values() for error in group})

    return {
        "status": "pass" if not errors else "fail",
        "candidate": "agent-routekit 0.1.1",
        "product_revision_sha256": product_revision_sha256(),
        "root": ".",
        "checks": {name: "pass" if not group else "fail" for name, group in check_errors.items()},
        "asset_sha256": asset_hashes,
        "errors": errors,
    }


def main() -> int:
    """Run the release validator CLI and render human or JSON output."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit the full JSON validation receipt.")
    args = parser.parse_args()
    result = run_validation()
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "pass":
        print("PASS: Local Model Route Planner release candidate")
    else:
        print("FAIL: Local Model Route Planner release candidate", file=sys.stderr)
        for error in result["errors"]:
            print(f"- {error}", file=sys.stderr)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
