# Release Checklist

## Product contract

- [x] Name: `agent-routekit`
- [x] Owner and publisher: `SpannDaMan`
- [x] License: MIT
- [x] Codex-first product surface
- [ ] 30-day maintainer pilot (starts only after public release; not completed)

## Local hardening gates

- [ ] Targeted unit, evaluation, renderer, package-install, Codex, Claude, and release-validator evidence is current for the candidate bytes.
- [ ] The transparent asset family is hash-bound and passes alpha, safe-fill, and renderer QA checks.
- [ ] Public documentation contains no private-source references, local paths, container identifiers, or conversation URLs.
- [ ] A clean standalone history and candidate-owned remote exist.
- [ ] One final frozen-candidate full gate records all accepted evidence hashes.

## Root-owned publication gate

- [ ] Create `SpannDaMan/agent-routekit` as a new public repository.
- [ ] Push only the reviewed standalone history.
- [ ] Enable Discussions and private vulnerability reporting if approved.
- [ ] Set topics and social preview.
- [ ] Create and verify `v0.1.0`.
- [ ] Test install from the actual Git source in a clean Codex environment.
- [ ] Publish the approved launch post.

Do not check the publication items until root-owned integration has produced a clean standalone history and a passing frozen-candidate gate.
