# Finding kinds

## Merge

- Two or more rows state the same obligation: the same actor, the same repository kind, the same stage, the same condition, and the same result.
- The requirement or the ADR survives when it has the same number of tests or more.
- A sentence that only one row states is not repeated text. Do not list it.

## Shorten

- The rows stay. A sentence that another row already states goes from this row. A sentence that the same row states twice also goes. Name that row as `same row`.
- Name the row that keeps the sentence. Quote the sentence that goes.
- A sentence with a number, a name, or a condition that the other row lacks stays.

## Covered by code

- The row has at least one test with an `id:` line for it.
- The column `names` of `make board-numbers` lists these tests as `file::name`. Read each such test. Every fact of the row must be pinned by an assertion: each name, number, list, path, and string.
- The row then shrinks to its intent and its reason.
- A cover finding has no size limit. Report it however few words the shrink saves.
- Keep what code cannot state: the reason, the rejected alternative, and a rule that crosses files.
- A fact that no assertion pins stays in the row. If one fact stays, say which.

## Delete history

- The file has the status `closed`. A file with the status `started` is never a finding.
- Read the Plan, Develop, and Review sections. A sentence that gives a reason or a rejected alternative is a reason.
- If no row or ADR that the file names states that reason, the file holds the only copy. Flag the file, quote the reason, and name the row that receives it. The words after are the words of that one sentence.
- A living document that links to the history id keeps a dead link. Count those in the links column. `r-board-merge` edits each out.

## Contradiction

- Two rows or files state opposite or unequal facts about one thing. A scope sentence or a list that differs counts.
- A contradiction is not a duplicate. Do not merge the two units.
- Read the code. The code is `skills/*/SKILL.md` and its references, `skills/*/*.mk`, templates, scripts, `Makefile`, `CLAUDE.md`, and `README.md`. In a product repository it is the source, the tests, and the makefiles.
- If the code decides, name the row that is false, the evidence as path and line, and the corrected sentence.
- If the code does not decide, the finding is a question to the owner. List the choices. `r-board-merge` does not touch it until the owner answers.

## Against code

- One row states something that the code does not do or does differently. A row that names a file, a target, a variable, or a skill that does not exist counts.
- Search the code for each name. Quote the path and line, or say that the search found none.
- If the code is right, name the evidence and the corrected sentence. The fix is a row edit.
- If the row may be right and the code wrong, the finding is a question to the owner with the choices. The fix is then a task for `r-develop`, not a row edit.

## Refutation

- Read both units in full.
- Same subject but another actor, another repository kind (this collection, a product repository, both), or another stage means no merge.
- A sentence that starts with `This applies to` names the repository kind.
- The same refutation applies to a contradiction. Two rows for two actors do not contradict.
