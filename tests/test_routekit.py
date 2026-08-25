from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "agent-routekit"
SCRIPT_PATH = PLUGIN_ROOT / "scripts" / "routekit.py"
REGISTRY_PATH = PLUGIN_ROOT / "routes.example.json"
DEMO_PATH = REPO_ROOT / "tools" / "demo.py"

SPEC = importlib.util.spec_from_file_location("routekit", SCRIPT_PATH)
assert SPEC and SPEC.loader
routekit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routekit)


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def task(**overrides: object) -> dict:
    value = {
        "id": "test-task",
        "summary": "Exercise the routing policy.",
        "complexity": "routine",
        "risk": "low",
        "minimum_quality": "routine",
        "required_capabilities": ["analysis"],
        "independent_review": False,
    }
    value.update(overrides)
    return value


class RouteKitTests(unittest.TestCase):
    def test_registry_is_valid(self) -> None:
        registry = routekit.validate_registry(load_registry())
        self.assertEqual(registry["schema_version"], "1.0")
        self.assertEqual(len(registry["routes"]), 5)

    def test_routine_task_uses_least_cost_route(self) -> None:
        receipt = routekit.plan_route(load_registry(), task())
        self.assertEqual(receipt["execution"]["route_id"], "swift")
        self.assertFalse(receipt["verification"]["required"])
        self.assertIsNone(receipt["verification"]["route"])

    def test_high_risk_task_requires_independent_review(self) -> None:
        receipt = routekit.plan_route(
            load_registry(),
            task(
                complexity="complex",
                risk="high",
                minimum_quality="high",
                required_capabilities=["analysis", "coding", "tool-use"],
            ),
        )
        self.assertEqual(receipt["execution"]["route_id"], "deep")
        self.assertTrue(receipt["verification"]["required"])
        self.assertEqual(receipt["verification"]["route"]["route_id"], "independent-review")
        self.assertNotEqual(
            receipt["execution"]["independence_group"],
            receipt["verification"]["route"]["independence_group"],
        )

    def test_novel_work_escalates_to_frontier(self) -> None:
        receipt = routekit.plan_route(
            load_registry(),
            task(
                complexity="novel",
                risk="medium",
                minimum_quality="standard",
                required_capabilities=["research"],
            ),
        )
        self.assertEqual(receipt["execution"]["route_id"], "frontier")

    def test_missing_capability_fails_closed(self) -> None:
        with self.assertRaisesRegex(routekit.RouteKitError, "no eligible execution route"):
            routekit.plan_route(
                load_registry(),
                task(required_capabilities=["hardware-control"]),
            )

    def test_missing_independent_verifier_fails_closed(self) -> None:
        registry = copy.deepcopy(load_registry())
        registry["routes"] = [route for route in registry["routes"] if "verify" not in route["roles"]]
        with self.assertRaisesRegex(routekit.RouteKitError, "no verifier is eligible"):
            routekit.plan_route(registry, task(risk="high", minimum_quality="high"))

    def test_same_independence_group_is_rejected(self) -> None:
        registry = copy.deepcopy(load_registry())
        reviewer = next(route for route in registry["routes"] if route["id"] == "independent-review")
        reviewer["independence_group"] = "deep-execution"
        registry["routes"] = [route for route in registry["routes"] if route["id"] != "frontier"]
        with self.assertRaisesRegex(routekit.RouteKitError, "not independent"):
            routekit.plan_route(
                registry,
                task(
                    complexity="complex",
                    risk="high",
                    minimum_quality="high",
                    required_capabilities=["tool-use"],
                ),
            )

    def test_review_uses_lowest_cost_complete_plan(self) -> None:
        registry = copy.deepcopy(load_registry())
        reviewer = next(route for route in registry["routes"] if route["id"] == "independent-review")
        reviewer["independence_group"] = "deep-execution"

        receipt = routekit.plan_route(
            registry,
            task(
                complexity="complex",
                risk="high",
                minimum_quality="high",
                required_capabilities=["tool-use"],
            ),
        )

        self.assertEqual(receipt["execution"]["route_id"], "frontier")
        self.assertEqual(receipt["verification"]["route"]["route_id"], "independent-review")
        deep_rejection = next(
            item for item in receipt["rejected_execution_routes"] if item["route_id"] == "deep"
        )
        self.assertEqual(
            deep_rejection["reasons"],
            ["no eligible independent verifier for this execution route"],
        )

    def test_receipt_is_deterministic(self) -> None:
        first = routekit.plan_route(load_registry(), task())
        second = routekit.plan_route(load_registry(), task())
        self.assertEqual(first, second)
        self.assertEqual(len(first["decision_id"]), 16)
        self.assertEqual(len(first["task"]["fingerprint"]), 64)

    def test_duplicate_route_id_is_rejected(self) -> None:
        registry = load_registry()
        registry["routes"].append(copy.deepcopy(registry["routes"][0]))
        with self.assertRaisesRegex(routekit.RouteKitError, "duplicated"):
            routekit.validate_registry(registry)

    def test_unknown_registry_field_is_rejected(self) -> None:
        registry = load_registry()
        registry["fallback"] = "silent"
        with self.assertRaisesRegex(routekit.RouteKitError, "unknown fields: fallback"):
            routekit.validate_registry(registry)

    def test_unknown_task_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(routekit.RouteKitError, "unknown fields: priority"):
            routekit.validate_task(task(priority="urgent"))

    def test_cli_text_receipt(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "plan",
                "--registry",
                str(REGISTRY_PATH),
                "--task",
                str(PLUGIN_ROOT / "examples" / "high-risk-task.json"),
                "--format",
                "text",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AGENT ROUTEKIT ROUTING RECEIPT", result.stdout)
        self.assertIn("executor: deep", result.stdout)
        self.assertIn("verifier: independent-review", result.stdout)

    def test_cli_validate_task(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "validate-task",
                "--task",
                str(PLUGIN_ROOT / "examples" / "routine-task.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["task_id"], "format-release-notes")

    def test_cli_can_write_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "receipt.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "plan",
                    "--registry",
                    str(REGISTRY_PATH),
                    "--task",
                    str(PLUGIN_ROOT / "examples" / "routine-task.json"),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), json.loads(result.stdout))

    def test_policy_bound_receipt_exposes_no_execution_boundary(self) -> None:
        receipt = routekit.plan_route(load_registry(), task())
        self.assertEqual(receipt["tool"], {"name": "agent-routekit", "version": "0.1.3"})
        self.assertIn("did not call a provider", receipt["no_execution_boundary"])
        self.assertTrue(receipt["assumptions"])
        self.assertTrue(receipt["unresolved_evidence"])

    def test_outcome_reconciliation_is_deterministic_and_noncausal(self) -> None:
        receipt = routekit.plan_route(load_registry(), task())
        outcome = {
            "schema_version": "1.0",
            "decision_id": receipt["decision_id"],
            "evidence_source": "independent host-neutral fixture",
            "observed_route_id": receipt["execution"]["route_id"],
            "metrics": [
                {"name": "latency", "unit": "ms", "baseline": 120, "observed": 100, "direction": "lower_is_better"}
            ],
            "limitations": ["Representative fixture only."],
            "routekit_non_collection_statement": "RouteKit did not collect or execute this outcome.",
        }
        first = routekit.reconcile_outcome(receipt, outcome)
        second = routekit.reconcile_outcome(receipt, outcome)
        self.assertEqual(first, second)
        self.assertEqual(first["metric_deltas"][0]["delta"], -20)
        self.assertEqual(first["metric_deltas"][0]["interpretation"], "not_interpreted")
        self.assertIn("does not claim causation", first["claim_boundary"])

    def test_outcome_reconciliation_rejects_wrong_route_or_execution_claim(self) -> None:
        receipt = routekit.plan_route(load_registry(), task())
        outcome = {
            "schema_version": "1.0",
            "decision_id": receipt["decision_id"],
            "evidence_source": "independent evidence",
            "observed_route_id": "different-route",
            "metrics": [{"name": "cost", "unit": "usd", "baseline": 2, "observed": 1, "direction": "lower_is_better"}],
            "limitations": ["Bounded fixture."],
            "routekit_non_collection_statement": "RouteKit did not collect or execute this outcome.",
        }
        with self.assertRaisesRegex(routekit.RouteKitError, "observed_route_id"):
            routekit.reconcile_outcome(receipt, outcome)
        outcome["observed_route_id"] = receipt["execution"]["route_id"]
        outcome["routekit_non_collection_statement"] = "RouteKit executed this outcome."
        with self.assertRaisesRegex(routekit.RouteKitError, "exact RouteKit non-collection statement"):
            routekit.validate_outcome_attachment(outcome)

    def test_outcome_reconciliation_rejects_tampered_planning_decision(self) -> None:
        receipt = routekit.plan_route(load_registry(), task())
        outcome = {
            "schema_version": "1.0",
            "decision_id": receipt["decision_id"],
            "evidence_source": "independent evidence",
            "observed_route_id": receipt["execution"]["route_id"],
            "metrics": [{"name": "latency", "unit": "ms", "baseline": 5, "observed": 4, "direction": "lower_is_better"}],
            "limitations": ["Bounded fixture."],
            "routekit_non_collection_statement": "RouteKit did not collect or execute this outcome.",
        }
        tampered = copy.deepcopy(receipt)
        tampered["execution"]["route_id"] = "tampered-route"
        with self.assertRaisesRegex(routekit.RouteKitError, "decision_id does not match"):
            routekit.reconcile_outcome(tampered, outcome)

    def test_cli_version(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "routekit 0.1.3")

    def test_one_command_demo_matches_canonical_cli(self) -> None:
        demo = subprocess.run(
            [sys.executable, str(DEMO_PATH)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        canonical = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "plan",
                "--registry",
                str(REGISTRY_PATH),
                "--task",
                str(PLUGIN_ROOT / "examples" / "high-risk-task.json"),
                "--format",
                "text",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertEqual(canonical.returncode, 0, canonical.stderr)
        self.assertEqual(demo.stdout, canonical.stdout)
        self.assertIn("decision: 20fcf65b051dd038", demo.stdout)


if __name__ == "__main__":
    unittest.main()
