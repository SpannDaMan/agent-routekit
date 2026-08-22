# Routing Contract

Agent RouteKit separates eligibility from ranking.

## 1. Normalize inputs

The registry and task must use schema version `1.0`. Unknown fields, duplicate route IDs, duplicate roles, duplicate capabilities, invalid levels, and empty required strings are rejected.

## 2. Derive the quality floor

The planner maps quality, complexity, and risk to a four-level ordinal scale and uses the maximum declared requirement as the binding quality floor.

## 3. Determine eligible executors

An execution route is eligible only when it:

- declares the `execute` role;
- meets the derived quality floor;
- supports the task complexity and risk;
- declares every required capability.

If no executor is eligible, planning stops with exit code `2`.

## 4. Rank eligible executors

Eligible routes are ordered by:

1. lowest `cost_rank`;
2. lowest sufficient quality rank;
3. stable route ID order.

Cost never makes an ineligible route eligible.

## 5. Require independent review

Review is required when the task requests it or the task risk is `high` or `critical`. A verifier must:

- declare the `verify` role;
- meet the same quality, complexity, and risk floor;
- declare the `review` capability;
- use a different `independence_group` from its execution route.

When review is required, the planner evaluates verifier feasibility for every eligible executor. It
then selects the lowest-ranked executor that admits at least one independent verifier, followed by
the lowest-ranked verifier for that executor. A cheaper executor without an eligible verifier cannot
invalidate a complete executor/verifier plan.

If review is required and no eligible executor/verifier pair exists, planning stops with exit code `2`.

## 6. Emit a deterministic receipt

The normalized task and registry are serialized with sorted keys and compact separators before SHA-256 hashing. The decision ID is derived from the task fingerprint, registry fingerprint, executor, and verifier. Identical normalized inputs produce identical receipts.

The receipt is planning evidence only. Runtime selection and execution require separate host evidence.
