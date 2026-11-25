---
name: review
description: Checks a change after implementation and before it ships. Runs the gates and each check row in docs/skill-index.toon, checks the change against the accepted ADRs, and writes findings through record. Use after develop and before release.
---

The general rules in `CLAUDE.md` apply.

<purpose>
`review` is the stage between `develop` and `release`. It finds each rule that the change breaks and records each break as a finding.
</purpose>

<steps>
1. Read `docs/skill-index.toon`. For each row whose `kind` is `check`, in file order, read that skill and run its checks. Write the line with the result, as `security: no secret in the diff, input checked.` If a check does not apply to this change, the line says why.
2. Read `docs/adr/index.toon`. Open the ADRs that step 3 of `develop` selects. In a repository with no `docs/adr/`, run `make req ID=<ids>` for the rows that step selects. A change that breaks one of them is a finding.
3. Run `make lint` and `make test`.
4. Check each test of the change against the test-id rule in `record`. If a test has an id in a path, stop.
5. Check the change against each rule under "Gates" in the general rules, and compare the code with the pattern that `plan` named. A break of a rule is a finding. Code that ignores the pattern is a finding. Write the method rule, the name rule, and the pattern as one check.
6. Run `make project-report` as steps 1 and 2 of `project-report` say. Stop also if a person edited `build/project-report.md`.
7. Read the list of ids with no test in `build/project-report.md`. If an ADR or a requirement row in force states behaviour of the code and has no test, write a finding. If the ADR or the row is a rule about how to work, write it under what was left alone.
8. Run `make links-check`. An id in a document that is not a link is a finding. `make links` fixes it.
9. Read `build/coverage/diff.md`. A repository-wide percentage that the change gives as its result is a finding.
10. If the repository has a CI workflow, read each workflow step. A `run:` step that is not `make <target>` is a finding. A step that runs `make test-changed` is a finding, because `test-changed` is not a CI target.
11. A finding that is fixed stays in this change. Ask `record` for a roadmap row of the kind `defect` for each finding that waits.
12. Ask `record` to write the Review section. The section holds the line for each check row, each finding, each gate that did not run, and what this change deliberately left alone.
</steps>

<rules>
- A finding states the location, the mechanism, the evidence, whether it predates this change, and the check that proves the fix.
- A finding about a model change or a prompt change needs a baseline from the same session.
- An accepted ADR replaces a skill rule only if the ADR is a divergence. An ADR that differs from a skill rule and does not name the three parts of a divergence is a finding.
- A divergence that the contract reference of `github-pipeline` lists as not allowed is a finding, also when an ADR records it.
- `plan` chose the pattern. Do not name a different pattern.
</rules>

<example>
"Only one package starts the command" is behaviour of the code. It needs a test.
"The engine is Podman" is a rule about how to work. It needs no test.
</example>
