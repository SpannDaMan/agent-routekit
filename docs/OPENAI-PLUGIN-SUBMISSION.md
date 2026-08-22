# OpenAI/Codex Plugin Submission Packet

Agent RouteKit is prepared as a skills-only plugin. It has no MCP server, UI, product-managed credentials, network access, telemetry, or hosted data storage.

## Local package

- Plugin root: `plugins/agent-routekit`
- OpenAI/Codex manifest: `plugins/agent-routekit/.codex-plugin/plugin.json`
- Skill: `plugins/agent-routekit/skills/agent-routekit/SKILL.md`
- Local CLI: `plugins/agent-routekit/scripts/routekit.py`
- Public submission data: `submission/openai-plugin-submission.json`

## Submission prerequisites

Before submitting through the OpenAI Platform:

1. Confirm the transparent asset receipt and current targeted validation evidence remain bound to the product revision.
2. Publish the reviewed repository under `SpannDaMan/agent-routekit` through the root-owned Git flow.
3. Confirm the public website, support, privacy, and terms URLs resolve.
4. Complete any publisher identity verification required by the owning OpenAI organization.
5. Upload the final skills-only archive and inspect the generated `.codex-plugin/plugin.json`.
6. Run every positive and negative case in `submission/openai-plugin-submission.json`.
7. Submit for review only after the root-owned frozen-candidate gate passes.

OpenAI review and directory publication are external actions. A valid local package is not review approval or public availability.
