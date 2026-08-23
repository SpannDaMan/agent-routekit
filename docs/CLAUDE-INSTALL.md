# Install In Claude Code

Local Model Route Planner ships as a skills-only Claude Code plugin. It does not install an MCP server, request credentials, or make network calls.

After the repository is public:

```text
/plugin marketplace add SpannDaMan/agent-routekit
/plugin install agent-routekit@agent-routekit
```

The skill is exposed under the plugin namespace. Start a new Claude Code session after installation so the current plugin snapshot is loaded.

## Local validation

From the repository root:

```bash
claude plugin validate .
claude plugin marketplace add .
```

The second command is for local testing only. Do not confuse a successful local install with acceptance into Anthropic's official marketplace.

## Optional command-line tool

The plugin skill can use the bundled `scripts/routekit.py` file. Installing the repository as a Python package additionally provides the global `agent-routekit` command:

```bash
python -m pip install .
agent-routekit --version
```

See [SUPPORT.md](../SUPPORT.md) for the supported boundary.
