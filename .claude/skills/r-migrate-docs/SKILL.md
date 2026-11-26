---
name: r-migrate-docs
description: Moves an old board onto the roadmap, the requirements, the ADRs, and the proposals, then deletes the old files. Use when `make old-board` fails or AGENTS.md exists.
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill moves each still-true fact of the old board to the new board and deletes the old board. The old board is the eight paths `docs/BUGS.md`, `docs/WAVES.md`, `docs/FEATURES.md`, `docs/DECISIONS.md`, `docs/KNOWN_ISSUES.md`, `docs/bugs/`, `docs/waves/`, and `docs/features/`. A `docs/ROADMAP.md` with a line that starts with `- ` instead of a table row is old board too. `make old-board` runs nine checks: the eight paths and this old form of the roadmap.
</purpose>

<steps>
1. Run `make old-board`, or `make -f .claude/skills/r-project-setup/old-board.mk old-board` when the Makefile has no include. The target prints each of the eight paths that exists, an empty directory too, and a `docs/ROADMAP.md` that has a line starting with `- `. It fails when one of the nine checks finds something. If the target passes and `AGENTS.md` does not exist, stop. There is nothing to migrate.
2. Move each still-true fact once. The rules below name the new place.
3. If `docs/ids.yaml` has the old form, a list `retired:` and no counter, delete it with `git rm`. Then ask `r-record` to give each kind of old label that was used as an id a counter: `make id-raise KIND=<kind> TO=<highest number used>`. Do it before you run `make ids`, which fails on an old label until its kind has a counter. The old label is not issued again, because the counter only grows. Name the old label in the text of the new row or file, so that a person can still find it. Change each `id:` line of a test that names an old label to the new id. A history file or an ADR with the keys `decisions` or `issues` keeps them. Do not rewrite a history file.
4. If `AGENTS.md` exists, move each constraint that is still true into `CLAUDE.md` and run `git rm AGENTS.md`. If `CLAUDE.md` does not exist, write it with the project title, the one sentence of `README.md` that says what the project is, and the constraints.
5. Run `make old-board-delete` in the same change, or `make -f .claude/skills/r-migrate-docs/migrate.mk old-board-delete` when the Makefile has no include. The target deletes the eight paths and then runs `make old-board`, which fails while `docs/ROADMAP.md` still has the old line form. Run no other skill until it passes.
6. Commit the files that this skill wrote or deleted. If `origin` exists, push.
</steps>

<rules>
- An open bug, an open audit finding, and a row of `docs/KNOWN_ISSUES.md` go to `docs/ROADMAP.md` as a row of the kind `defect`.
- An Open row of `docs/DECISIONS.md` goes to `docs/ROADMAP.md` as a row of the kind `question` when it waits for an answer, and as a row of the kind `feature` otherwise.
- Work that is already in progress goes to `docs/ROADMAP.md` as a row of the kind `feature`. Each line of an old `docs/ROADMAP.md` becomes such a row, with the title of its history file. If that history file does not exist, the title is the text of the line, and the old history id stays in the title as plain text. Write the table over the old file. The file then has the layout of the `r-record` template.
- A feature or a wave that is a plan for later goes to `docs/ROADMAP.md` as a row of the kind `feature`, with a file in `docs/proposals/`. The old text is the slice sentence. In `Out of scope` and in the questions, write that `r-plan` asks them when the proposal is picked up.
- A Decided row of `docs/DECISIONS.md` goes where `r-record` decides, as the choice rule of `r-record` says: a requirement row, a sentence in an ADR, or a new ADR. If no home fits, ask the user. A Decided row that need not hold, or that an installed skill or an accepted ADR already states, is not moved.
- An architecture or development rule goes to `docs/adr/`, with `adrs:` and `skills:`.
- Do not copy a fixed bug, a shipped feature, or a wave narrative. If one of its sentences is still a rule, the choice rule of `r-record` places that sentence.
</rules>
