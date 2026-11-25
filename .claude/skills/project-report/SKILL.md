---
name: project-report
description: Generates the project report from the board and the tests. Use when the requirements-to-tests map, the architecture review, or the development review is needed.
---

The general rules in `CLAUDE.md` apply.

<purpose>
`make project-report` writes `build/project-report.md`. The file has three sections, so that `review` reads one file: the requirements-to-tests map, the architecture review, and the development review.
</purpose>

<steps>
1. Run `make project-report`. If the target fails, stop. If the output names a test file with no id, read `references/report-contents.md`.
2. Read `build/project-report.md`. If the requirements map, the architecture review, or the development review is missing, stop.
3. Report each id that the map lists with no test. `review` says whether that rule needs a test.
</steps>

<rules>
- A test file with no id fails the target. A test that names an id that is not a requirement fails the target. An id with no test is listed and does not fail the target.
- The map lists ADR ids and the ids of requirement rows in force. The map does not list a superseded ADR as an id with no test. The map does not list a roadmap row or a planned row. The two reviews list them.
- The two reviews are lists of the rules in force, the open work, and the numbered steps of the stages. They are not a judgement.
- `report.mk` beside this skill owns the `project-report` target. `project.mk` and `sdlc.mk` include that file when this skill is installed.
</rules>

<references>
- `references/report-contents.md`: read it when the target names a test file with no id, when a test or an id is absent from the map, when a review misses an entry, or when the project sets `PROJECT_REPORT_CMD`.
</references>
