#!/usr/bin/env python3
"""Deterministic, provider-neutral model-route planning with receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


RECEIPT_VERSION = "1.0"
REGISTRY_VERSION = "1.0"
VERSION = "0.1.4"
OUTCOME_BOUNDARY_STATEMENT = "RouteKit did not collect or execute this outcome."

QUALITY_LEVELS = {"routine": 1, "standard": 2, "high": 3, "critical": 4}
COMPLEXITY_LEVELS = {"routine": 1, "standard": 2, "complex": 3, "novel": 4}
RISK_LEVELS = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ALLOWED_ROLES = {"execute", "verify"}
REGISTRY_FIELDS = {"schema_version", "routes"}
ROUTE_FIELDS = {
    "id",
    "roles",
    "model",
    "effort",
    "owner",
    "independence_group",
    "cost_rank",
    "quality_level",
    "max_complexity",
    "max_risk",
    "capabilities",
}
TASK_FIELDS = {
    "id",
    "summary",
    "complexity",
    "risk",
    "minimum_quality",
    "required_capabilities",
    "independent_review",
}


class RouteKitError(ValueError):
    """Raised when an input cannot produce a safe routing decision."""


def _load_json(path: str | Path) -> Any:
    """Load a UTF-8 JSON document and convert read or parse failures into RouteKit errors."""

    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RouteKitError(f"cannot read {source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RouteKitError(f"invalid JSON in {source}: {exc}") from exc


def _canonical_json(value: Any) -> str:
    """Serialize a value into the stable representation used for fingerprints."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fingerprint(value: Any) -> str:
    """Return the SHA-256 digest of a value's canonical JSON representation."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_string(value: Any, label: str) -> str:
    """Normalize one required non-empty string or raise a labelled validation error."""

    if not isinstance(value, str) or not value.strip():
        raise RouteKitError(f"{label} must be a non-empty string")
    return value.strip()


def _require_level(value: Any, label: str, levels: dict[str, int]) -> str:
    """Normalize and validate one named ordinal level."""

    normalized = _require_string(value, label).lower()
    if normalized not in levels:
        allowed = ", ".join(levels)
        raise RouteKitError(f"{label} must be one of: {allowed}")
    return normalized


def _require_string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    """Normalize a duplicate-free list of non-empty strings."""

    if not isinstance(value, list):
        raise RouteKitError(f"{label} must be a list of strings")
    if not allow_empty and not value:
        raise RouteKitError(f"{label} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise RouteKitError(f"{label} must contain only non-empty strings")
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        raise RouteKitError(f"{label} must not contain duplicates")
    return normalized


def _reject_unknown_fields(value: dict[str, Any], allowed: set[str], label: str) -> None:
    """Reject input fields that are outside the versioned RouteKit contract."""

    unknown = sorted(set(value) - allowed)
    if unknown:
        raise RouteKitError(f"{label} contains unknown fields: {', '.join(unknown)}")


def validate_registry(registry: Any) -> dict[str, Any]:
    """Validate and normalize a RouteKit registry."""

    if not isinstance(registry, dict):
        raise RouteKitError("registry must be a JSON object")
    _reject_unknown_fields(registry, REGISTRY_FIELDS, "registry")
    if registry.get("schema_version") != REGISTRY_VERSION:
        raise RouteKitError(f"registry schema_version must be {REGISTRY_VERSION}")

    raw_routes = registry.get("routes")
    if not isinstance(raw_routes, list) or not raw_routes:
        raise RouteKitError("registry.routes must be a non-empty list")

    normalized_routes: list[dict[str, Any]] = []
    route_ids: set[str] = set()
    for index, raw_route in enumerate(raw_routes):
        label = f"routes[{index}]"
        if not isinstance(raw_route, dict):
            raise RouteKitError(f"{label} must be an object")
        _reject_unknown_fields(raw_route, ROUTE_FIELDS, label)

        route_id = _require_string(raw_route.get("id"), f"{label}.id")
        if route_id in route_ids:
            raise RouteKitError(f"route id is duplicated: {route_id}")
        route_ids.add(route_id)

        roles = _require_string_list(raw_route.get("roles"), f"{label}.roles", allow_empty=False)
        unknown_roles = sorted(set(roles) - ALLOWED_ROLES)
        if unknown_roles:
            raise RouteKitError(f"{label}.roles contains unsupported values: {', '.join(unknown_roles)}")

        cost_rank = raw_route.get("cost_rank")
        if isinstance(cost_rank, bool) or not isinstance(cost_rank, int) or cost_rank < 1:
            raise RouteKitError(f"{label}.cost_rank must be a positive integer")

        normalized_routes.append(
            {
                "id": route_id,
                "roles": roles,
                "model": _require_string(raw_route.get("model"), f"{label}.model"),
                "effort": _require_string(raw_route.get("effort"), f"{label}.effort"),
                "owner": _require_string(raw_route.get("owner"), f"{label}.owner"),
                "independence_group": _require_string(
                    raw_route.get("independence_group"), f"{label}.independence_group"
                ),
                "cost_rank": cost_rank,
                "quality_level": _require_level(
                    raw_route.get("quality_level"), f"{label}.quality_level", QUALITY_LEVELS
                ),
                "max_complexity": _require_level(
                    raw_route.get("max_complexity"), f"{label}.max_complexity", COMPLEXITY_LEVELS
                ),
                "max_risk": _require_level(raw_route.get("max_risk"), f"{label}.max_risk", RISK_LEVELS),
                "capabilities": _require_string_list(
                    raw_route.get("capabilities"), f"{label}.capabilities"
                ),
            }
        )

    if not any("execute" in route["roles"] for route in normalized_routes):
        raise RouteKitError("registry must include at least one execution route")

    return {"schema_version": REGISTRY_VERSION, "routes": normalized_routes}


def validate_task(task: Any) -> dict[str, Any]:
    """Validate and normalize one task description."""

    if not isinstance(task, dict):
        raise RouteKitError("task must be a JSON object")
    _reject_unknown_fields(task, TASK_FIELDS, "task")

    independent_review = task.get("independent_review", False)
    if not isinstance(independent_review, bool):
        raise RouteKitError("task.independent_review must be true or false")

    return {
        "id": _require_string(task.get("id"), "task.id"),
        "summary": _require_string(task.get("summary"), "task.summary"),
        "complexity": _require_level(task.get("complexity"), "task.complexity", COMPLEXITY_LEVELS),
        "risk": _require_level(task.get("risk"), "task.risk", RISK_LEVELS),
        "minimum_quality": _require_level(
            task.get("minimum_quality"), "task.minimum_quality", QUALITY_LEVELS
        ),
        "required_capabilities": _require_string_list(
            task.get("required_capabilities", []), "task.required_capabilities"
        ),
        "independent_review": independent_review,
    }


def _required_quality_rank(task: dict[str, Any]) -> int:
    """Derive the hard quality floor from every declared task constraint."""

    return max(
        QUALITY_LEVELS[task["minimum_quality"]],
        COMPLEXITY_LEVELS[task["complexity"]],
        RISK_LEVELS[task["risk"]],
    )


def _route_rejection_reasons(
    route: dict[str, Any],
    task: dict[str, Any],
    required_quality_rank: int,
    *,
    role: str,
    executor: dict[str, Any] | None = None,
) -> list[str]:
    """Explain every hard constraint that makes a route ineligible for one role."""

    reasons: list[str] = []
    if role not in route["roles"]:
        reasons.append(f"does not declare the {role} role")
    if QUALITY_LEVELS[route["quality_level"]] < required_quality_rank:
        reasons.append("quality level is below the derived floor")
    if COMPLEXITY_LEVELS[route["max_complexity"]] < COMPLEXITY_LEVELS[task["complexity"]]:
        reasons.append("complexity ceiling is too low")
    if RISK_LEVELS[route["max_risk"]] < RISK_LEVELS[task["risk"]]:
        reasons.append("risk ceiling is too low")

    if role == "execute":
        missing = sorted(set(task["required_capabilities"]) - set(route["capabilities"]))
        if missing:
            reasons.append(f"missing capabilities: {', '.join(missing)}")
    else:
        if "review" not in route["capabilities"]:
            reasons.append("missing review capability")
        if executor and route["independence_group"] == executor["independence_group"]:
            reasons.append("not independent from the execution route")
    return reasons


def _sort_key(route: dict[str, Any]) -> tuple[int, int, str]:
    """Return the deterministic cost, quality, and route-ID ranking key."""

    return (route["cost_rank"], QUALITY_LEVELS[route["quality_level"]], route["id"])


def _public_route(route: dict[str, Any]) -> dict[str, Any]:
    """Project a normalized registry route into the public receipt shape."""

    return {
        "route_id": route["id"],
        "model": route["model"],
        "effort": route["effort"],
        "owner": route["owner"],
        "cost_rank": route["cost_rank"],
        "quality_level": route["quality_level"],
        "independence_group": route["independence_group"],
    }


def plan_route(registry: Any, task: Any) -> dict[str, Any]:
    """Choose a safe executor and optional verifier, then return a receipt."""

    clean_registry = validate_registry(registry)
    clean_task = validate_task(task)
    quality_floor = _required_quality_rank(clean_task)
    review_required = clean_task["independent_review"] or RISK_LEVELS[clean_task["risk"]] >= 3

    execution_evaluations: list[dict[str, Any]] = []
    eligible_executors: list[dict[str, Any]] = []
    for route in clean_registry["routes"]:
        reasons = _route_rejection_reasons(route, clean_task, quality_floor, role="execute")
        execution_evaluations.append({"route_id": route["id"], "reasons": reasons})
        if not reasons:
            eligible_executors.append(route)

    if not eligible_executors:
        detail = "; ".join(
            f"{item['route_id']}: {', '.join(item['reasons'])}"
            for item in execution_evaluations
        )
        raise RouteKitError(f"no eligible execution route; {detail}")

    executor: dict[str, Any]
    verifier: dict[str, Any] | None = None
    verification_evaluations: list[dict[str, Any]] = []
    executors_without_verifier: set[str] = set()
    if review_required:
        verifier_options: dict[str, list[dict[str, Any]]] = {}
        verifier_evaluations: dict[str, list[dict[str, Any]]] = {}
        for candidate in eligible_executors:
            candidate_evaluations: list[dict[str, Any]] = []
            candidate_verifiers: list[dict[str, Any]] = []
            for route in clean_registry["routes"]:
                reasons = _route_rejection_reasons(
                    route,
                    clean_task,
                    quality_floor,
                    role="verify",
                    executor=candidate,
                )
                candidate_evaluations.append({"route_id": route["id"], "reasons": reasons})
                if not reasons:
                    candidate_verifiers.append(route)
            verifier_evaluations[candidate["id"]] = candidate_evaluations
            verifier_options[candidate["id"]] = candidate_verifiers
            if not candidate_verifiers:
                executors_without_verifier.add(candidate["id"])

        complete_executors = [
            candidate
            for candidate in eligible_executors
            if verifier_options[candidate["id"]]
        ]
        if not complete_executors:
            detail = " | ".join(
                f"{candidate['id']} -> "
                + "; ".join(
                    f"{item['route_id']}: {', '.join(item['reasons'])}"
                    for item in verifier_evaluations[candidate["id"]]
                )
                for candidate in sorted(eligible_executors, key=_sort_key)
            )
            raise RouteKitError(
                "independent review is required but no verifier is eligible "
                f"for any execution route; {detail}"
            )

        executor = sorted(complete_executors, key=_sort_key)[0]
        verification_evaluations = verifier_evaluations[executor["id"]]
        verifier = sorted(verifier_options[executor["id"]], key=_sort_key)[0]
    else:
        executor = sorted(eligible_executors, key=_sort_key)[0]

    task_fingerprint = _fingerprint(clean_task)
    registry_fingerprint = _fingerprint(clean_registry)
    decision_material = {
        "task_fingerprint": task_fingerprint,
        "registry_fingerprint": registry_fingerprint,
        "executor": executor["id"],
        "verifier": verifier["id"] if verifier else None,
    }
    decision_id = _fingerprint(decision_material)[:16]

    rejected_execution_routes: list[dict[str, Any]] = []
    for evaluation in execution_evaluations:
        if evaluation["route_id"] == executor["id"]:
            continue
        reasons = evaluation["reasons"]
        if not reasons and evaluation["route_id"] in executors_without_verifier:
            reasons = ["no eligible independent verifier for this execution route"]
        elif not reasons:
            reasons = ["eligible but ranked after the selected lower-cost route"]
        rejected_execution_routes.append({"route_id": evaluation["route_id"], "reasons": reasons})

    verification: dict[str, Any] = {"required": review_required, "route": None, "rejected_routes": []}
    if verifier:
        verification["route"] = _public_route(verifier)
        verification["rejected_routes"] = [
            {
                "route_id": evaluation["route_id"],
                "reasons": evaluation["reasons"]
                or ["eligible but ranked after the selected lower-cost verifier"],
            }
            for evaluation in verification_evaluations
            if evaluation["route_id"] != verifier["id"]
        ]

    if verifier:
        reason = (
            f"Selected {executor['id']} as the lowest-cost eligible execution route with an "
            f"eligible independent verifier after enforcing quality floor {quality_floor}/4, "
            f"{clean_task['complexity']} complexity, {clean_task['risk']} risk, and all required "
            f"capabilities. Selected {verifier['id']} as the lowest-cost eligible independent "
            "verifier."
        )
    else:
        reason = (
            f"Selected {executor['id']} as the lowest-cost eligible execution route "
            f"after enforcing quality floor {quality_floor}/4, {clean_task['complexity']} complexity, "
            f"{clean_task['risk']} risk, and all required capabilities."
        )

    policy = {
        "registry_fingerprint": registry_fingerprint,
        "required_quality_rank": quality_floor,
        "complexity": clean_task["complexity"],
        "risk": clean_task["risk"],
        "required_capabilities": clean_task["required_capabilities"],
        "independent_review_required": review_required,
    }
    return {
        "receipt_version": RECEIPT_VERSION,
        "tool": {"name": "agent-routekit", "version": VERSION},
        "decision_id": decision_id,
        "task": {"id": clean_task["id"], "fingerprint": task_fingerprint},
        "policy": policy,
        "fingerprints": {"policy": _fingerprint(policy), "registry": registry_fingerprint},
        "execution": _public_route(executor),
        "eligible_alternatives": [
            _public_route(candidate)
            for candidate in sorted(eligible_executors, key=_sort_key)
            if candidate["id"] != executor["id"]
        ],
        "verification": verification,
        "reason": reason,
        "rejected_execution_routes": rejected_execution_routes,
        "limitations": [
            "This receipt records a planning decision; it does not prove runtime model selection.",
            "Model and effort values are registry labels whose availability must be verified by the host.",
        ],
        "assumptions": [
            "Registry labels and policy inputs are caller-supplied declarations.",
            "Cost rank is ordinal policy data, not a live provider price.",
        ],
        "unresolved_evidence": [
            "Selected route availability at execution time.",
            "Independent runtime outcome and observed cost or quality metrics.",
        ],
        "no_execution_boundary": "Local Model Route Planner planned this decision locally and did not call a provider, execute a model, dispatch a runtime, or collect an outcome.",
    }


def validate_outcome_attachment(payload: Any) -> dict[str, Any]:
    """Validate independently supplied outcome evidence without interpreting quality."""

    if not isinstance(payload, dict):
        raise RouteKitError("outcome attachment must be an object")
    fields = {
        "schema_version",
        "decision_id",
        "evidence_source",
        "observed_route_id",
        "metrics",
        "limitations",
        "routekit_non_collection_statement",
    }
    _reject_unknown_fields(payload, fields, "outcome attachment")
    if set(payload) != fields or payload.get("schema_version") != "1.0":
        raise RouteKitError("outcome attachment fields or schema_version are invalid")
    decision_id = _require_string(payload.get("decision_id"), "outcome attachment.decision_id")
    if len(decision_id) != 16 or any(character not in "0123456789abcdef" for character in decision_id):
        raise RouteKitError("outcome attachment.decision_id must be a 16-character lowercase hex value")
    evidence_source = _require_string(payload.get("evidence_source"), "outcome attachment.evidence_source")
    observed_route_id = _require_string(payload.get("observed_route_id"), "outcome attachment.observed_route_id")
    statement = _require_string(
        payload.get("routekit_non_collection_statement"),
        "outcome attachment.routekit_non_collection_statement",
    )
    if statement != OUTCOME_BOUNDARY_STATEMENT:
        raise RouteKitError("outcome attachment must use the exact RouteKit non-collection statement")
    limitations = _require_string_list(payload.get("limitations"), "outcome attachment.limitations", allow_empty=False)
    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not metrics or len(metrics) > 50:
        raise RouteKitError("outcome attachment.metrics must contain 1 to 50 entries")
    normalized_metrics: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(metrics):
        label = f"outcome attachment.metrics[{index}]"
        if not isinstance(raw, dict):
            raise RouteKitError(f"{label} must be an object")
        metric_fields = {"name", "unit", "baseline", "observed", "direction"}
        _reject_unknown_fields(raw, metric_fields, label)
        if set(raw) != metric_fields:
            raise RouteKitError(f"{label} fields are invalid")
        name = _require_string(raw.get("name"), f"{label}.name")
        if name in names:
            raise RouteKitError(f"outcome metric is duplicated: {name}")
        unit = _require_string(raw.get("unit"), f"{label}.unit")
        direction = _require_string(raw.get("direction"), f"{label}.direction")
        if direction not in {"higher_is_better", "lower_is_better", "context_only"}:
            raise RouteKitError(f"{label}.direction is invalid")
        baseline = raw.get("baseline")
        observed = raw.get("observed")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in (baseline, observed)):
            raise RouteKitError(f"{label} baseline and observed values must be finite numbers")
        names.add(name)
        normalized_metrics.append(
            {
                "name": name,
                "unit": unit,
                "baseline": baseline,
                "observed": observed,
                "direction": direction,
            }
        )
    return {
        "schema_version": "1.0",
        "decision_id": decision_id,
        "evidence_source": evidence_source,
        "observed_route_id": observed_route_id,
        "metrics": sorted(normalized_metrics, key=lambda item: item["name"].casefold()),
        "limitations": limitations,
        "routekit_non_collection_statement": OUTCOME_BOUNDARY_STATEMENT,
    }


def _planning_receipt_context(planning_receipt: Any) -> tuple[str, str]:
    """Validate the decision binding required for deterministic reconciliation."""

    if not isinstance(planning_receipt, dict):
        raise RouteKitError("planning receipt must be an object")
    if planning_receipt.get("receipt_version") != RECEIPT_VERSION:
        raise RouteKitError("planning receipt version is unsupported")
    decision_id = _require_string(planning_receipt.get("decision_id"), "planning receipt.decision_id")
    if len(decision_id) != 16 or any(character not in "0123456789abcdef" for character in decision_id):
        raise RouteKitError("planning receipt.decision_id is invalid")
    task = planning_receipt.get("task")
    policy = planning_receipt.get("policy")
    execution = planning_receipt.get("execution")
    verification = planning_receipt.get("verification")
    if not all(isinstance(item, dict) for item in (task, policy, execution, verification)):
        raise RouteKitError("planning receipt decision fields are invalid")
    task_fingerprint = _require_string(task.get("fingerprint"), "planning receipt.task.fingerprint")
    registry_fingerprint = _require_string(policy.get("registry_fingerprint"), "planning receipt.policy.registry_fingerprint")
    selected_route_id = _require_string(execution.get("route_id"), "planning receipt.execution.route_id")
    verifier = verification.get("route")
    if verifier is not None and not isinstance(verifier, dict):
        raise RouteKitError("planning receipt.verification.route must be an object or null")
    verifier_id = (
        _require_string(verifier.get("route_id"), "planning receipt.verification.route.route_id")
        if verifier is not None
        else None
    )
    expected_decision_id = _fingerprint(
        {
            "task_fingerprint": task_fingerprint,
            "registry_fingerprint": registry_fingerprint,
            "executor": selected_route_id,
            "verifier": verifier_id,
        }
    )[:16]
    if decision_id != expected_decision_id:
        raise RouteKitError("planning receipt decision_id does not match its bound decision fields")
    fingerprints = planning_receipt.get("fingerprints")
    if not isinstance(fingerprints, dict) or set(fingerprints) != {"policy", "registry"}:
        raise RouteKitError("planning receipt fingerprints are invalid")
    if fingerprints.get("registry") != registry_fingerprint or fingerprints.get("policy") != _fingerprint(policy):
        raise RouteKitError("planning receipt fingerprints are inconsistent")
    return decision_id, selected_route_id


def reconcile_outcome(planning_receipt: Any, outcome_attachment: Any) -> dict[str, Any]:
    """Bind one planning receipt to independently supplied outcome evidence."""

    decision_id, selected_route_id = _planning_receipt_context(planning_receipt)
    clean_outcome = validate_outcome_attachment(outcome_attachment)
    if clean_outcome["decision_id"] != decision_id:
        raise RouteKitError("outcome attachment decision_id does not match the planning receipt")
    if clean_outcome["observed_route_id"] != selected_route_id:
        raise RouteKitError("outcome attachment observed_route_id does not match the selected route")
    metric_deltas = [
        {
            "name": metric["name"],
            "unit": metric["unit"],
            "baseline": metric["baseline"],
            "observed": metric["observed"],
            "delta": metric["observed"] - metric["baseline"],
            "direction": metric["direction"],
            "interpretation": "not_interpreted",
        }
        for metric in clean_outcome["metrics"]
    ]
    planning_fingerprint = _fingerprint(planning_receipt)
    outcome_fingerprint = _fingerprint(clean_outcome)
    return {
        "schema_version": "1.0",
        "artifact": "Local Model Route Planner Outcome Reconciliation Receipt",
        "tool": {"name": "agent-routekit", "version": VERSION},
        "decision_id": decision_id,
        "reconciliation_id": _fingerprint(
            {
                "decision_id": decision_id,
                "planning_receipt": planning_fingerprint,
                "outcome_attachment": outcome_fingerprint,
            }
        )[:16],
        "selected_route_id": selected_route_id,
        "planning_receipt_sha256": planning_fingerprint,
        "outcome_attachment_sha256": outcome_fingerprint,
        "evidence_source": clean_outcome["evidence_source"],
        "metric_deltas": metric_deltas,
        "limitations": clean_outcome["limitations"],
        "status": "reconciled_without_causal_interpretation",
        "claim_boundary": "Binds a planning receipt to independently supplied observations only; RouteKit did not execute or collect the outcome and does not claim causation, runtime quality, or live cost accuracy.",
    }


def _format_text(receipt: dict[str, Any]) -> str:
    """Render a routing receipt as stable human-readable text."""

    executor = receipt["execution"]
    verification = receipt["verification"]
    verifier = verification["route"]
    verifier_text = (
        f"{verifier['route_id']} ({verifier['model']}, {verifier['effort']})"
        if verifier
        else "not required"
    )
    lines = [
        "AGENT ROUTEKIT ROUTING RECEIPT",
        f"decision: {receipt['decision_id']}",
        f"task: {receipt['task']['id']}",
        f"executor: {executor['route_id']} ({executor['model']}, {executor['effort']})",
        f"owner: {executor['owner']}",
        f"verifier: {verifier_text}",
        f"quality floor: {receipt['policy']['required_quality_rank']}/4",
        f"risk: {receipt['policy']['risk']}",
        f"reason: {receipt['reason']}",
        "limitation: planning evidence only; runtime execution must be proven separately.",
    ]
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line contract for validation and planning commands."""

    parser = argparse.ArgumentParser(
        prog="routekit",
        description="Plan a quality-first model route and emit a deterministic receipt.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-registry", help="Validate a route registry.")
    validate.add_argument("--registry", required=True, help="Path to a RouteKit registry JSON file.")

    validate_task_parser = subparsers.add_parser("validate-task", help="Validate a task description.")
    validate_task_parser.add_argument("--task", required=True, help="Path to a RouteKit task JSON file.")

    plan = subparsers.add_parser("plan", help="Plan one task route.")
    plan.add_argument("--registry", required=True, help="Path to a RouteKit registry JSON file.")
    plan.add_argument("--task", required=True, help="Path to a RouteKit task JSON file.")
    plan.add_argument("--format", choices=("json", "text"), default="json")
    plan.add_argument("--output", help="Optional path to write the rendered receipt.")

    reconcile = subparsers.add_parser("reconcile", help="Reconcile a planning receipt with independent outcome evidence.")
    reconcile.add_argument("--receipt", required=True, help="Path to a RouteKit planning receipt JSON file.")
    reconcile.add_argument("--outcome", required=True, help="Path to an independent outcome attachment JSON file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the RouteKit CLI and return a stable process exit code."""

    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate-registry":
            registry = _load_json(args.registry)
            normalized = validate_registry(registry)
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "schema_version": normalized["schema_version"],
                        "route_count": len(normalized["routes"]),
                        "registry_fingerprint": _fingerprint(normalized),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "validate-task":
            clean_task = validate_task(_load_json(args.task))
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "task_id": clean_task["id"],
                        "task_fingerprint": _fingerprint(clean_task),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "reconcile":
            result = reconcile_outcome(_load_json(args.receipt), _load_json(args.outcome))
            print(json.dumps(result, indent=2))
            return 0

        registry = _load_json(args.registry)
        task = _load_json(args.task)
        receipt = plan_route(registry, task)
        if args.format == "text":
            rendered = _format_text(receipt)
        else:
            rendered = json.dumps(receipt, indent=2)
        if args.output:
            destination = Path(args.output)
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(rendered + "\n", encoding="utf-8")
            except OSError as exc:
                raise RouteKitError(f"cannot write {destination}: {exc}") from exc
        print(rendered)
        return 0
    except RouteKitError as exc:
        print(f"routekit: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
