# Close mode

Do these steps in order after step 1 of close mode has passed.

1. Set the history status to `closed`.
2. Delete each roadmap row that `roadmap:` of the history file names. A defect and a question are roadmap rows too. The counter of `docs/ids.yaml` keeps the number, so it is never issued again. Read `docs/ROADMAP.md` again and stop if a row still has the id.
3. If a test still names a deleted roadmap id, stop. The test must name a rule, as the test rules of `SKILL.md` say. Ask `record` to write the rule first, as `SKILL.md` says about a choice that must hold.
4. If the slice started from a proposal, set the proposal status to `done`.
5. Leave each ADR and each requirement row. They stay in force.
6. In a repository that keeps `docs/requirements/` and no `docs/adr/`, set the status of the planned row for this task to `in force`. If the task left no rule, delete the row.

A task whose work waits stays open. A slice that is done and waits only for the merge of the owner is closed on its branch.
