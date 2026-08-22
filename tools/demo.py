#!/usr/bin/env python3
"""Run Agent RouteKit's deterministic high-risk example from any platform."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "agent-routekit"


def main() -> int:
    """Delegate to the canonical CLI so the demo cannot drift from the product."""

    command = [
        sys.executable,
        str(PLUGIN / "scripts" / "routekit.py"),
        "plan",
        "--registry",
        str(PLUGIN / "routes.example.json"),
        "--task",
        str(PLUGIN / "examples" / "high-risk-task.json"),
        "--format",
        "text",
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
