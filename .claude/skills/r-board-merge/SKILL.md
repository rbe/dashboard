---
name: r-board-merge
description: Applies the findings that the owner chose by id from the board merge report. Merges rows, shortens a row, shrinks a row that tests cover, deletes a closed history file, or fixes a row to a corrected sentence. Makes one commit for each finding.
---

The general rules in `CLAUDE.md` apply.

<purpose>
The owner chooses findings from the report of `r-board-merge-report`. This skill does exactly that and nothing else. One Git commit holds one finding, so that `git revert` undoes one. This skill never changes code.
</purpose>

<inputs>
- An action and ids, as `merge R-51 R-76`, `shorten R-12`, `cover R-40`, `delete H-2026-11-15-slug`, or `fix R-12`.
- Several lines make several findings. Edit one finding and commit it before the first edit of the next. Two findings in one file then stay in two commits.
- A question of the report waits for the owner's answer.
</inputs>

<steps>
1. Run `make toon` and `make board-numbers IDS="<ids>"`. Keep the output as the words before. If an id is not a unit, stop.
2. Check the finding again, because the report can be old. Read `references/recheck.md`. If a check fails, stop and tell the user the id and the reason.
3. Invoke `r-record` before each board write. Edit the row text with the file edit tool. Do the action as the rules say.
4. Run `make links`, `make toon`, `make ids`, and `make links-check`.
5. Run the gates of `CLAUDE.md`. If a gate fails, stop without a commit. Leave the edit in the working tree, name the gate, and say that a fix or `git checkout -- <files>` is the next step.
6. Run `make board-numbers IDS="<the surviving or receiving id>"`. Its words are the words after. A deletion with no moved reason has 0.
7. Stage only the files of the finding and commit with Git. The message names the action, the ids, and the words before and after. Then start the next finding at step 1.
</steps>

<rules>
- Merge: the surviving row keeps its id and takes the unique sentences of the other row. The row of the other id is deleted. Its number is never issued again.
- Merge: each test line `id:` that names the deleted id names the surviving id. The column `names` of `make board-numbers` lists these tests. No test is deleted.
- Merge: each mention of the deleted id in a document that is not a history file becomes the surviving id before the delete. Then `make links` rewrites the links. Edit no line of a history file.
- Shorten and cover: edit the row only. Cover keeps the intent, the reason, and each fact that no test pins.
- Delete history: copy a flagged reason into the named row first. Remove each mention of the history id outside history files, and delete the file.
- Fix: edit the row to the corrected sentence of the finding, after the check of the evidence. Change no code and no test.
- Touch no id outside the finding.
</rules>

<output>
- For each finding: the action, the ids, the commit, the gates and their results, and the words before and after.
- A finding that stopped: the id, the step, and the reason.
</output>

<references>
- `references/recheck.md`: what to check again for each action. Read it in step 2.
</references>
