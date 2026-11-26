# What the project report reads

## Requirements-to-tests map

- The map names which tests prove each requirement id, and which ids have no test.
- The test rules of `r-record` state the form of the `id:` line. In a Python test, the test is the proof. In a test file of another language, the file is the proof.
- A file under `.claude/`, `apm_modules/`, `node_modules/`, or `build/` is not a project test. The map does not read it.

## Sources of the two reviews

| Review | Board documents | Numbered steps of |
| --- | --- | --- |
| Architecture review | ADRs, roadmap | `r-plan`, `r-review` |
| Development review | ADRs, roadmap, planned requirement rows | `r-develop`, `r-review`, `r-release`, `r-project-setup` |

If a review misses a step of a skill, check that the step is numbered and stands in the first `<steps>` block of that skill. For `r-project-setup`, the block is the first `<checks>` block.

## The target

`report.mk` sets `PROJECT_REPORT_CMD` only when the project did not set it. A project that sets `PROJECT_REPORT_CMD` replaces the command, and `report.mk` still owns the `project-report` target.
