# Security Policy

Local Model Route Planner is a local planner. It requires no credentials, network access, hosted service, or model-provider connection.

## Supported versions

During the 30-day maintainer pilot, the latest `0.1.x` release is supported. Security fixes may be released as a new patch version.

## Report a vulnerability

After publication, use GitHub private vulnerability reporting for `SpannDaMan/agent-routekit`. Do not open a public issue for an unpatched vulnerability or include private task content, credentials, tokens, internal paths, or exploit data in a public discussion.

Before the repository exists, security intake remains closed because there is no approved public delivery surface.

## Scope

Relevant reports include:

- a routing decision that bypasses declared quality, risk, capability, or independence constraints;
- receipt nondeterminism for identical normalized inputs;
- path traversal or unintended file writes from CLI input or output handling;
- sensitive data exposure beyond the fields documented in the receipt contract;
- plugin packaging that includes credentials, private paths, or unreviewed executable content.

Model-provider behavior, runtime model execution, and the security of a caller's orchestration layer are outside RouteKit's runtime boundary.
