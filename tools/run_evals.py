#!/usr/bin/env python3
"""Run the bounded public Agent RouteKit evaluation suite."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "agent-routekit"
SUITE_PATH = ROOT / "evals" / "agent-routekit-suite.json"
RECEIPT_PATH = ROOT / "validation" / "Agent RouteKit Eval Result 220826.json"


def load_routekit() -> Any:
    spec = importlib.util.spec_from_file_location("agent_routekit_eval", PLUGIN / "scripts" / "routekit.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_suite() -> dict[str, Any]:
    suite = load_json(SUITE_PATH)
    routekit = load_routekit()
    registry = load_json(PLUGIN / "routes.example.json")
    results: list[dict[str, Any]] = []
    for case in suite["cases"]:
        task_value = case["task"]
        task = load_json(ROOT / task_value) if isinstance(task_value, str) else task_value
        result: dict[str, Any] = {"id": case["id"], "status": "pass"}
        try:
            receipt = routekit.plan_route(registry, task)
            if "expected_error" in case:
                raise AssertionError("expected a fail-closed error but received a receipt")
            if receipt["execution"]["route_id"] != case["expected_execution_route"]:
                raise AssertionError("unexpected execution route")
            if receipt["verification"]["required"] != case["expected_verification_required"]:
                raise AssertionError("unexpected verification requirement")
            if "expected_verifier_route" in case:
                verifier = receipt["verification"]["route"]
                if not verifier or verifier["route_id"] != case["expected_verifier_route"]:
                    raise AssertionError("unexpected verifier route")
            result["decision_id"] = receipt["decision_id"]
        except Exception as exc:  # Expected fail-closed cases are asserted below.
            if "expected_error" in case and case["expected_error"] in str(exc):
                result["expected_error"] = case["expected_error"]
            else:
                result["status"] = "fail"
                result["error"] = str(exc)
        results.append(result)
    return {
        "schema_version": "1.0",
        "candidate": "agent-routekit 0.1.2",
        "suite_id": suite["suite_id"],
        "status": "pass" if all(item["status"] == "pass" for item in results) else "fail",
        "case_count": len(results),
        "results": results,
        "publication_action": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-receipt", action="store_true", help="Write the candidate-bound evaluation receipt.")
    args = parser.parse_args()
    result = run_suite()
    validator_spec = importlib.util.spec_from_file_location("release_validator", ROOT / "tools" / "validate_release_candidate.py")
    assert validator_spec and validator_spec.loader
    validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator)
    result["product_revision_sha256"] = validator.product_revision_sha256()
    if args.write_receipt:
        RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
