# Close mode

Do these steps in order after step 1 of close mode has passed.

1. Set the history status to `closed`.
2. Delete each roadmap row that `roadmap:` of the history file names. A defect and a question are roadmap rows too. The counter of `docs/ids.yaml` keeps the number, so it is never issued again. Read `docs/ROADMAP.md` again and stop if a row still has the id.
3. If a test still names a deleted roadmap id, stop. The test must name a rule, as the test rules of `SKILL.md` say. Ask `r-record` to write the rule first, as `SKILL.md` says about a choice that must hold.
4. If the slice started from a proposal, delete the file `docs/proposals/<id>.md`. Git keeps its text. The history file keeps the id in `proposals:`.
5. Shorten the history file to at most 150 words below its frontmatter. Keep the four headings. Keep what changed, the ids, the gate results, and what was not run. Git keeps the full text.
6. Leave each ADR and each requirement row. They stay in force.
7. In a repository that keeps `docs/requirements/` and no `docs/adr/`, set the status of the planned row for this task to `in force`. If the task left no rule, delete the row.

A task whose work waits stays open. A slice that is done and waits only for the merge of the owner is closed on its branch.
