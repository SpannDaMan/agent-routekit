# 30-Day Maintainer Pilot

The pilot begins on the date `v0.1.0` is publicly released. No pilot has started or completed for this local candidate.

## Purpose

Test whether Local Model Route Planner creates retained developer value and whether SpannDaMan can maintain it without creating an open-ended support burden.

## Maintainer commitment

- Triage new issues at least twice per week.
- Target an initial response within five business days.
- Prioritize incorrect routing, missing fail-closed behavior, nondeterminism, install failures, and sensitive-data risks.
- Keep the core standard-library-only during the pilot unless a dependency is justified by a demonstrated blocker.
- Publish no patch without the unit suite, release validator, plugin validator, and clean-install checks.

## Measures

Record weekly:

- successful installs or confirmed first runs;
- reproducible defects and time to first response;
- incorrect route or verifier decisions;
- forks and pull requests that demonstrate real use;
- repeat users, issue follow-through, and documentation questions;
- stars as an attention signal, not the primary success measure;
- maintainer hours and unresolved support inventory.

## Success condition

Continue after day 30 when all of the following are true:

- at least five independently confirmed successful installs or first runs;
- no unresolved critical routing or security defect;
- at least two signals of retained use, such as a repeat issue participant, useful fork, pull request, or integration report;
- median first response is five business days or less;
- maintenance averages no more than three hours per week.

## Pause or narrow condition

Pause new features and ship only fixes when a high-risk routing defect or sensitive-data issue is open. Narrow or archive the project when maintenance exceeds six hours in two consecutive weeks without retained-use evidence, or when the product promise cannot be demonstrated reliably in under five minutes.

## Day-30 decision

Choose one: continue, narrow scope, merge the concept into another project, transfer maintenance, or archive. Record the decision and evidence in a GitHub issue or release note after the operator approves that external action.
