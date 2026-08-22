# Codex Installation

## Public Git marketplace

After the repository is published:

```text
codex plugin marketplace add SpannDaMan/agent-routekit
codex plugin add agent-routekit@agent-routekit
```

The marketplace command accepts `owner/repo`, an HTTPS Git URL, an SSH Git URL, or a local path. Start a new Codex task after installation so the plugin skill is included in the new prompt.

## Local candidate

Before publication, use a local marketplace path supported by your installed Codex version:

```text
codex plugin marketplace add <local-path-to-agent-routekit>
codex plugin add agent-routekit@agent-routekit
```

This changes the local Codex plugin configuration. Local package validation does not silently install the candidate into an active profile.

## Verify the installed payload

Do not rely on a list entry alone. In a fresh task, ask Codex to “Route this task and show me the receipt” and confirm that the `agent-routekit` skill is present. Then run the registry and high-risk demo commands from the README.

## Remove

Use the current `codex plugin` help for the installed version before removal. Plugin-management syntax is versioned and should be verified rather than copied from stale documentation.
