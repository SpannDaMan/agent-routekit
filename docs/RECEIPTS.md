# Routing Receipts

A receipt answers five questions:

1. Which execution route was selected?
2. Was independent review required, and which verifier was selected?
3. Which quality, complexity, risk, and capability constraints bound the decision?
4. Why were other routes rejected or ranked later?
5. Which limitations still apply?

## Privacy behavior

The receipt includes the task ID and a SHA-256 fingerprint of the normalized task. It does not include the task summary. Use a sanitized task ID because IDs may still reveal project or customer information.

## Determinism

Fingerprints and decision IDs are content-derived. No clock, host path, random value, or provider response is included. The same normalized task and registry yield the same JSON receipt.

## Output

```text
agent-routekit plan \
  --registry routes.json \
  --task task.json \
  --format json \
  --output receipt.json
```

Text format is intended for humans. JSON format is intended for tests, CI, and host orchestration.

## Runtime evidence

Do not treat the receipt as proof that the selected model or agent ran. A host integration should attach its own execution identity, timestamps, tool results, and verifier evidence without changing the RouteKit planning receipt.
