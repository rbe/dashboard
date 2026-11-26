---
name: r-record
description: Assigns ids and writes the board documents and the indexes. Use before creating or editing a roadmap row, a requirement row, an ADR, a proposal, or a history file, and to close a task. Rejects a duplicate id and an id above its counter.
---

The general rules in `CLAUDE.md` apply.

<purpose>
The agent writes each document by hand from a template in `templates/` beside this skill, and `make ids` checks the ids, and `make id` issues each new id.
</purpose>

<mode name="write">
<steps>
1. Run `make ids`. If it exits non-zero, an id is a duplicate or above its counter: stop and do not write the document. In step 3 of `r-migrate-docs`, a failure that names an old label with no counter does not stop you. Without the include of `project.mk` or `sdlc.mk`, run `make -f .claude/skills/r-record/index.mk <target>`. `PYTHON_IMAGE=<image>` on that line replaces the default image.
2. For a new item, run `make id KIND=<kind>`. It prints the next id and raises the counter. Read `references/id-kinds.md` for the form of each kind.
3. If the document does not exist, copy its template: `ROADMAP.md`, `adr.md`, `proposal.md`, or `history.md`. Keep the layout. Before you write frontmatter or a table row for the first time in a task, read `references/documents.md`.
4. If a choice must hold, read `references/adr.md` and write it where it says. If no home fits, ask the user.
5. If the document is an ADR, follow `references/adr.md`.
6. If the caller asks for a new history file or for a stage section, read `references/history.md`. Write a new file from `templates/history.md`. Set `roadmap:` to the row of the task, and add that row when the task has none.
7. If a stage asks for its section, write it in sentences: what the stage did, each gate with its result, and what the stage left alone. Replace `Not invoked yet.` and keep the heading. Update the frontmatter lists.
8. If another skill asks for its line, add the line to the section of the stage that runs, as `python: the language skill for the Python files.` or `security: no listener, no secret.` Add the skill name to `skills` in the frontmatter. That skill opens no history file. If no history file is open, add no line.
9. If a document or a table row is deleted, delete it and nothing else. The counter keeps its number. No document is rewritten.
10. If ADR frontmatter, a file of `docs/requirements/`, or the set of installed skills changed, run `make toon`. If `make toon` fails, read `references/indexes.md`.
</steps>
</mode>

<mode name="close">
<steps>
1. If the Plan, the Develop, or the Review section of the history file is still `Not invoked yet.`, stop.
2. Read `references/close.md` and do its steps in order.
</steps>
</mode>

<rules>
- Do the id check in this skill. Do not delegate it, and do not accept an id that the caller invented in prose.
- The next number of a kind comes from `make id KIND=<kind>`, never from a count by hand. The counter in `docs/ids.yaml` only grows, so a number is never issued twice.
- Write an id as plain text. After a document under `docs/` changes, run `make links`. It makes each id a link.
- A frontmatter list of ids follows `references/documents.md`: ids only, one form, and no id above its counter.
- A history file follows `references/history.md`: it holds facts only. Open work is a roadmap row, or a planned row of `docs/requirements/`.
- A defect and an open question are roadmap rows. A question row states the choices.
- A defect that the owner reports gets a roadmap row of the kind `defect` through `r-record`, then starts at `r-develop`. A defect with no known expected behaviour starts at `r-plan`.
- A question that the owner has not answered is never in a history file.
- To read one requirement row or one ADR, run `make req ID=<ids>`. To find rows, run `make req Q=<word>`, `OWNER=<skill>`, or `STATUS=planned`. Do not open a whole file of `docs/requirements/` for one row.
- A deleted id has no target. After the delete, run `make links`. A history file keeps the id as it is.
- One task has one history file. A deferred slice is a roadmap row with a proposal and has no history file.
- `r-onboard`, `r-migrate-docs`, and setup mode of `r-project-setup` open no history file, and their commits go on the default branch. An agent on another task opens a history file only when an id names it.
- `make ids` matches the `id:` line in the header or the metadata of a test. A roadmap row is work, not a rule, and it is deleted when the slice closes. A test does not name it.
- A test for a fixed defect names the ADR or the requirement row that states the fixed behaviour.
- The test name states what the system does when the requirement holds. The test does not build a path to the document.
</rules>

<references>
- `references/id-kinds.md`: the form, the first id, the status, and the counter of each kind. Read it when you take a new id.
- `references/documents.md`: the layouts the scripts read, the frontmatter keys, and what `make links` writes. Read it before the first write of frontmatter or of a table row in a task, and when `make links-check` fails.
- `references/adr.md`: where a choice goes, and the sections, the status, and `skills` of an ADR. Read it before you record a choice or write or supersede an ADR.
- `references/history.md`: the rules and the content of the history file and of each section. Read it before you create a history file or write a section, and when you are not sure what a section holds.
- `references/close.md`: the steps of close mode. Read it in close mode.
- `references/test-ids.md`: the form of the `id:` line in each language. Read it when you write or check an `id:` line.
- `references/indexes.md`: the files `make toon` writes, their columns, and why `make toon` fails. Read it when `make toon` fails or when a question is about an index.
</references>
