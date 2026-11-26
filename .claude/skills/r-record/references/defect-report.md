# Defect report

A defect report lets a person who was not in the conversation act on it. A finding of `r-review` and a defect of the owner use this form. Run each check you name before you write it.

1. Location: the path relative to the repository, and the line or the symbol.
2. Mechanism: what the code does, in its own characters. Name the function that computes the value and the function that does not use it.
3. Evidence: what you ran and what came back, with the input, the flags, or the fixture that make it appear again. A symptom with no reproduction is a suspicion.
4. Not a regression: say whether the defect predates the recent change, and how you know. Use a Git comparison of an older commit. If you could not tell, write "not established".
5. The rule it contradicts: the requirement row, ADR, or roadmap row that says otherwise, as `make req ID=<ids>` prints it. If none says otherwise, look for a decision before you file.
6. Fix options: what you would do, what else could work, a precedent in the tree, and what must not change.
7. Acceptance check: one command or one action that anyone can run without interpretation, and the test that fails without the fix. Name what the test asserts.
8. Documents to update: the board rows that mention the defect as a known gap, and when each update applies.

## Where it stands

- A defect that waits is a roadmap row of the kind `defect`. Its proposal file holds the report.
- A finding that is fixed in the change has parts 1 to 5 as sentences in the Review section of the history file.
- A report that hands the defect to an agent also gives the files that the agent owns, as the Agents section of `CLAUDE.md` says.
