#!/usr/bin/env python3
"""Run local Codex and Claude package validation and record revision-bound receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "agent-routekit"
VALIDATION_DIR = ROOT / "validation"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("release_validator", ROOT / "tools" / "validate_release_candidate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tool_identity(path: Path, name: str) -> dict[str, Any]:
    return {"name": name, "identity": "sha256", "sha256": sha256(path), "bytes": path.stat().st_size}


def execute(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    output = (completed.stdout + completed.stderr).strip().replace(str(ROOT), ".")
    return completed.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-receipts", action="store_true", help="Write candidate-bound Codex and Claude validation receipts.")
    args = parser.parse_args()

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    codex_validator = codex_home / "skills" / ".system" / "plugin-creator" / "scripts" / "validate_plugin.py"
    claude_executable = shutil.which("claude") or shutil.which("claude.cmd")
    if not codex_validator.is_file():
        raise SystemExit("Codex plugin validator is unavailable")
    if not claude_executable:
        raise SystemExit("Claude CLI is unavailable")

    revision = validator_module().product_revision_sha256()
    codex_code, codex_output = execute([sys.executable, str(codex_validator), str(PLUGIN)])
    claude_code, claude_output = execute([claude_executable, "plugin", "validate", "."])
    claude_path = Path(claude_executable)
    codex_receipt = {
        "schema_version": "1.0",
        "candidate": "agent-routekit 0.1.3",
        "product_revision_sha256": revision,
        "status": "pass" if codex_code == 0 else "fail",
        "exit_code": codex_code,
        "validated_plugin_path": "plugins/agent-routekit",
        "command": ["python", "validate_plugin.py", "plugins/agent-routekit"],
        "tool": tool_identity(codex_validator, "Codex plugin-creator validate_plugin.py"),
        "output": codex_output,
        "publication_action": "none",
    }
    claude_receipt = {
        "schema_version": "1.0",
        "candidate": "agent-routekit 0.1.3",
        "product_revision_sha256": revision,
        "status": "pass" if claude_code == 0 else "fail",
        "checks": [{"name": "claude_marketplace_manifest", "exit_code": claude_code, "output": claude_output}],
        "tool": tool_identity(claude_path, "Claude Code CLI"),
        "publication_action": "none",
    }
    result = {"codex": codex_receipt, "claude": claude_receipt}
    if args.write_receipts:
        VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
        (VALIDATION_DIR / "Codex Plugin Verification 220826.json").write_text(json.dumps(codex_receipt, indent=2) + "\n", encoding="utf-8")
        (VALIDATION_DIR / "Claude Plugin Verification 220826.json").write_text(json.dumps(claude_receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if codex_code == 0 and claude_code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
