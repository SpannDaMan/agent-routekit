from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "agent-routekit" / "scripts" / "routekit.py"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CaseError(ValueError):
    pass


def load_routekit():
    spec = importlib.util.spec_from_file_location("routekit_outcome_case_validator", SCRIPT)
    if spec is None or spec.loader is None:
        raise CaseError("cannot load the local Agent RouteKit module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CaseError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError, CaseError) as exc:
        raise CaseError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CaseError(f"{path.name} must contain a JSON object")
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseError(f"{label} must be a non-empty string")
    return value.strip()


def resolve_record(record: Any, label: str) -> tuple[Path, str]:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise CaseError(f"{label} fields are invalid")
    relative = text(record.get("path"), f"{label}.path")
    digest = text(record.get("sha256"), f"{label}.sha256")
    if not SHA256_RE.fullmatch(digest):
        raise CaseError(f"{label}.sha256 is invalid")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise CaseError(f"{label} escapes the repository") from exc
    if not path.is_file() or path.is_symlink():
        raise CaseError(f"{label} is missing or symlinked")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise CaseError(f"{label} digest does not match")
    return path, relative.replace("\\", "/")


def validate(manifest_path: Path) -> dict[str, Any]:
    routekit = load_routekit()
    manifest = load(manifest_path)
    if set(manifest) != {"schema_version", "required_case_count", "cases", "claim_boundary"} or manifest.get("schema_version") != "1.0" or manifest.get("required_case_count") != 1:
        raise CaseError("outcome case manifest identity or fields are invalid")
    boundary = text(manifest.get("claim_boundary"), "claim_boundary")
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise CaseError("cases must be a list")
    ids: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        expected = {"id", "planning_receipt", "outcome_attachment", "reconciliation_receipt", "host_independent", "evidence_source"}
        if not isinstance(case, dict) or set(case) != expected:
            raise CaseError(f"cases[{index}] fields are invalid")
        case_id = text(case.get("id"), f"cases[{index}].id")
        if case_id in ids or case.get("host_independent") is not True:
            raise CaseError(f"case identity or host-independent declaration is invalid: {case_id}")
        evidence_source = text(case.get("evidence_source"), f"{case_id}.evidence_source")
        planning_path, planning_relative = resolve_record(case.get("planning_receipt"), f"{case_id}.planning_receipt")
        outcome_path, outcome_relative = resolve_record(case.get("outcome_attachment"), f"{case_id}.outcome_attachment")
        reconciliation_path, reconciliation_relative = resolve_record(case.get("reconciliation_receipt"), f"{case_id}.reconciliation_receipt")
        planning = load(planning_path)
        outcome = load(outcome_path)
        stored = load(reconciliation_path)
        expected_reconciliation = routekit.reconcile_outcome(planning, outcome)
        if stored != expected_reconciliation:
            raise CaseError(f"{case_id} reconciliation receipt is stale or inconsistent")
        if outcome.get("evidence_source") != evidence_source:
            raise CaseError(f"{case_id} evidence source does not match the outcome attachment")
        ids.add(case_id)
        results.append(
            {
                "id": case_id,
                "planning_receipt": planning_relative,
                "outcome_attachment": outcome_relative,
                "reconciliation_receipt": reconciliation_relative,
                "host_independent": True,
                "status": "pass",
            }
        )
    status = "pass" if len(results) >= 1 and all(item["status"] == "pass" for item in results) else "hold"
    return {
        "schema_version": "1.0",
        "artifact": "Agent RouteKit Outcome Case Receipt",
        "required_case_count": 1,
        "observed_case_count": len(results),
        "results": results,
        "status": status,
        "claim_boundary": boundary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Agent RouteKit independent outcome case gate.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "evidence" / "outcome-case-manifest.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = validate(args.manifest)
        if args.json:
            print(json.dumps(receipt, indent=2))
        else:
            print(f"{receipt['status'].upper()}: {receipt['observed_case_count']}/{receipt['required_case_count']} cases")
        return 0 if receipt["status"] == "pass" else 1
    except (CaseError, OSError, ValueError) as exc:
        print(f"outcome-case: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
