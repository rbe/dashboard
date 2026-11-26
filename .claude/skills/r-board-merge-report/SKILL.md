---
name: r-board-merge-report
description: Reports which board rows, ADRs, and closed history files can merge, shrink, or go, which rows contradict each other, and which rows differ from the code. Writes nothing. Use when the owner asks to cut board duplicates, clean the board, or check the board against the code.
---

The general rules in `CLAUDE.md` apply.

<purpose>
The report lists board text that says one fact twice, says opposite facts, or differs from the code. The owner reads it once and chooses by id what `r-board-merge` does. This skill writes no file, no row, and no id. It covers the documents in `docs/`. `r-skills-review` covers skill files.
</purpose>

<inputs>
- The scope is the requirement rows in force of the files in `docs/requirements/`, the ADRs in `docs/adr/`, and the files in `docs/history/`.
- Planned rows, roadmap rows, and proposals are out of scope.
- If `docs/adr/` does not exist, the ADR part is empty. Say so in one line.
</inputs>

<steps>
1. Run `make toon` and `make board-numbers`. If a target fails, stop. Do not count words, tests, or links yourself. Take the names of the tests from the column `names`. Open a test file only to read its assertions.
2. Read each row, ADR, or history file that the index or the numbers make a candidate. Open a unit in full before you quote it.
3. List the candidates of the six kinds. Read `references/finding-kinds.md` for the test of each kind.
4. Try to refute each merge candidate. If the actor, the repository kind, or the stage differs, drop it.
5. Read the code for each contradiction and each against-code candidate. The reference names the code and the form of the finding.
6. For each finding that stays, take the words now, the tests, and the links from the numbers. Write the words after as about.
7. Write the report. Read `references/report-form.md` for the tables.
</steps>

<rules>
- A merge keeps the id that more tests name. If the tests tie, it keeps the id with more links, then the lower number.
- A merge lists the tests (by the names of the column `names`) and the links that name the id that the merge deletes. The numbers count a frontmatter list of a history file. They do not count a link in its text. A history file keeps the deleted id.
- A history file is never merged. It is deleted only when it is closed.
- If a closed history file holds the only copy of a reason, say so. The reason moves to a row first.
- A row that no test names is never a covered-by-code finding. A covered-by-code finding has no size limit.
- A contradiction or against-code finding needs evidence as path and line. If the code does not decide, ask the owner. Never guess.
- Do not report an id of a planned row, a roadmap row, or a proposal.
- Invent no id. Use only ids that `make board-numbers` printed.
</rules>

<output>
- One table for each kind that has findings: Merge, Shorten, Covered by code, Delete history, Contradiction, Against code. A kind with none gets one line that says none.
- Each finding has a number, the ids, a short quote, and the columns of `references/report-form.md`.
- The reply says which units you read in full and how many you did not read.
- The last lines say how to choose, by ids: `merge R-51 R-76`, `shorten R-12`, `cover R-40`, `delete H-2026-11-15-slug`, `fix R-12`.
</output>

<references>
- `references/finding-kinds.md`: the test of each finding kind and the refutation. Read it in steps 3 and 5.
- `references/report-form.md`: the columns of each table and a sample. Read it in step 7.
</references>
