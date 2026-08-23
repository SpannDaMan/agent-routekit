# Release Evidence Contract

Local Model Route Planner binds generated local evidence to a non-self-referential product revision.

## Product revision digest

The product file set is every regular candidate file except files below `validation/`, `.git/`, build output, package metadata, and Python bytecode. Symlinks are forbidden.

For each included file, sort by POSIX-style relative path and append this UTF-8 record:

```text
relative_path<TAB>byte_count<TAB>file_sha256<LF>
```

The SHA-256 of the complete record sequence is `product_revision_sha256`. Because generated receipts live below `validation/`, writing current evidence does not change the product revision it attests.

## Required binding

The transparent-asset extraction, evaluation, Codex package, and Claude package receipts must record the exact current `product_revision_sha256`. The local release validator recomputes the digest and rejects stale receipts, missing required evidence, provider-package drift, generated residue, and opaque icon regressions.

This binding proves which product bytes a receipt names. It does not prove semantic equivalence, runtime execution, hosted behavior, marketplace approval, adoption, or demand.
