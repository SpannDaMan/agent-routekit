# Evaluation Guide

Agent RouteKit's release validation is not a substitute for behavioral evaluation.

The public candidate makes no provider-performance, pricing, availability, or runtime-execution claim. Its local evaluation tests the deterministic routing contract: routine least-cost selection, high-risk independent-review selection, and fail-closed behavior when a requirement cannot be met.

## Local suite

Run the committed suite from the repository root:

```text
python -B tools/run_evals.py --write-receipt
```

The runner executes the three representative cases in `evals/agent-routekit-suite.json`, validates their receipt shape, and writes a candidate-bound receipt under `validation/`.

## Interpretation

The evaluation proves deterministic behavior for the committed registry and task cases only. It does not prove that a host model ran, that a third-party registry is safe, that a route is available, or that a planned action is authorized.
