---
name: r-develop
description: Implements a closed slice plan with its tests, using the installed language skill for the files in hand. Use after r-plan, or when a request names a source file, a failing test, or a defect row of the roadmap. A fix starts here.
---

The general rules in `CLAUDE.md` apply.

<purpose>
`r-develop` changes the code and the tests of one slice, and it proves the change with the gates.
</purpose>

<steps>
1. Read the history file of the task.
   If there is none, create the branch of the slice with `git checkout -b <slug>` and ask `r-record` for a history file.
   The Plan section is then one sentence that says why `r-plan` was not invoked.
   If the slice starts from a proposal, the Plan section cites the proposal id.
2. Read `docs/skill-index.toon`. Invoke each `language` row whose `files` or `names` match the files in hand.
   Stop when a file set has no matching row.
   A document, such as `README.md` or a file under `docs/`, needs no language row.
3. Read `docs/adr/index.toon`. Open each ADR whose status is `Accepted` and whose `skills` names a skill that this slice uses.
   Stop when the change would break one of them.
4. If the files in hand have two languages, split them into two disjoint file sets. Finish one set before you edit the other.
5. Write the change, and write a unit test for each behaviour change.
   Stop when one target runs both unit tests and integration tests.
6. Give each test its `id:` line. The test rules of `r-record` state which id the line names and the form of the line in each language.
   If a test has no ADR and no requirement row to name, ask `r-record` where the choice goes, and name the new id.
7. Compare the change with the general rules on tests, fixtures, methods, and names. Stop when the change breaks one.
8. Run `make coverage`, then `make test-changed`.
   `make coverage` writes the coverage map, and `test-changed` selects the tests from that map. A green `test-changed` does not replace `make test`.
   Stop when the coverage map is missing.
9. Run `make lint` and `make test`. Stop when either target fails.
10. If a source or test file changed after the last run of `make coverage`, run `make coverage` again.
    Stop when `build/coverage/diff.md` is missing.
    If the change has only test files or documents, the report has no line. Write that in the Develop section.
11. Ask `r-record` to write the Develop section.
</steps>

<rules>
- The Develop section does not copy the proposal.
- A method that first rejects bad input and then does one computation does one thing.
</rules>
