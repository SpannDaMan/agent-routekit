# Contributing

The repository is not open for contributions until publication is approved.

After release:

1. Open a focused issue describing the user-visible routing problem.
2. Keep the core provider-neutral and standard-library-only unless a dependency has a concrete, reviewed benefit.
3. Add a focused test for every behavior change.
4. Preserve deterministic receipts and fail-closed independent review for high-risk work.
5. Run the first-change loop below before opening a pull request.

## First-change loop

From the repository root:

```text
python tools/demo.py
python -B -m unittest discover -s tests -v
python tools/validate_release_candidate.py
```

The demo is the fastest behavior check. The unit suite covers routing and failure paths. The release validator checks the public package, deterministic sample receipt, documentation, metadata, assets, and safety boundaries.

Never include credentials, private task content, internal paths, customer data, or real production prompts in fixtures, issues, receipts, or pull requests.

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md), and [THREAT-MODEL.md](THREAT-MODEL.md).
