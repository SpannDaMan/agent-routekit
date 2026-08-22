---
name: agent-routekit
description: "Plan the route, not the run: deterministically evaluate declared model or agent policies, require independent review for high-risk work, emit a Policy-Bound Route Receipt, or reconcile it with independently supplied outcome evidence without executing a provider."
---

# Agent RouteKit

Agent RouteKit is a planning and evidence skill. It does not invoke a model runtime or grant execution authority.

## Procedure

1. Translate the task into the task schema shown in `../../examples/`, preserving the user’s risk and quality requirements. Do not down-classify risk to obtain a cheaper route.
2. Use the plugin’s `../../routes.example.json` unless the user supplies a registry. Treat model and effort values as labels whose availability must be verified by the host environment.
3. Validate the registry before relying on it:

   ```text
   python <plugin-root>/scripts/routekit.py validate-registry --registry <registry.json>
   ```

4. Validate the task. Unknown fields are rejected so a misspelled requirement cannot be ignored:

   ```text
   python <plugin-root>/scripts/routekit.py validate-task --task <task.json>
   ```

5. Plan the route and retain the receipt:

   ```text
   python <plugin-root>/scripts/routekit.py plan --registry <registry.json> --task <task.json> --format json --output <receipt.json>
   ```

6. Explain the selected executor, any verifier, the binding quality/risk constraints, and important rejected alternatives.
7. If the host can delegate, execute only within the user’s existing authority and record separate runtime evidence. Never present the planning receipt as proof that the selected model actually ran.
8. Reconcile an outcome only from independently supplied evidence with matching decision and route IDs. Do not infer causation or fabricate missing metrics.

## Fail-closed rules

- High- or critical-risk work requires a verifier from a different `independence_group`.
- Missing capabilities, invalid configuration, or no eligible route is a blocker, not permission to improvise.
- Unknown task or registry fields are validation failures, not ignored extensions.
- The least-cost rule applies only after quality, complexity, risk, capability, and independence constraints pass.
- Never add credentials, private task data, or internal paths to a public registry or receipt.
