# Threat Model

## Assets to protect

- routing-policy integrity;
- deterministic decision and receipt behavior;
- sensitive task summaries and route registries;
- the independence boundary between executor and verifier;
- the clean plugin package and release history.

## Trust boundary

RouteKit reads local JSON files and optionally writes a local receipt. It does not call providers, execute the selected route, authenticate users, or verify runtime model selection. The caller owns filesystem permissions, model execution, runtime evidence, and any external effects.

## Main threats and controls

| Threat | Control |
| --- | --- |
| A misspelled policy key is silently ignored | Unknown registry and task fields are rejected. |
| Cost optimization bypasses quality or risk | Eligibility is enforced before cost ranking. |
| High-risk work uses a non-independent verifier | Verifier must use a different `independence_group`. |
| No verifier exists but execution continues | Planning fails closed with a nonzero exit code. |
| A receipt is presented as runtime proof | Every receipt carries an explicit limitation. |
| Sensitive text leaks through shared fixtures | Receipts retain task ID and fingerprint, not the task summary; docs require sanitized fixtures. |
| Output path is used for unexpected writes | RouteKit writes only the explicit `--output` file and reports write failures. |
| Release package includes private or secret material | Release validator scans paths, file shape, sensitive markers, secrets, manifests, and assets. |

## Residual risks

- A dishonest or misconfigured registry can overstate a model's real capability.
- Symbolic cost ranks are policy inputs, not verified provider prices.
- Identical labels do not prove actual provider or model independence.
- A host may ignore the receipt and execute a different route.
- Task IDs can still be sensitive if users put private information in them.

These risks require host-side availability checks, runtime receipts, careful registry ownership, and sanitized task identifiers.
