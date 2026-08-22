# Privacy

Agent RouteKit is a local, skills-only plugin and standard-library command-line tool.

## Data handling

- It does not send task files, registries, receipts, or validation results over the network.
- It does not include telemetry, analytics, advertising, hosted accounts, authentication, or tracking code.
- It does not require API keys or other credentials.
- Files are read from and written to paths selected by the user on the local machine.

RouteKit receipts include a task ID and a SHA-256 fingerprint of normalized task data. Task IDs can still reveal project or customer context; sanitize them before sharing receipts.

## Host products

When Agent RouteKit is installed through Codex, Claude Code, GitHub, or another host, that host's privacy terms and telemetry settings still apply to the host product. Agent RouteKit does not control or expand them.

## Contact

After publication, use the repository's security reporting path for private security concerns and GitHub Issues for non-sensitive privacy defects. See [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md).
