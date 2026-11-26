# Check again

Read each unit in full and run `make board-numbers IDS="<ids>"`. Stop at the first check that fails.

## All actions

- Each id is a unit in scope: a requirement row in force, an ADR, or a history file.
- The text of the report still holds. A row that changed since the report fails the check.

## merge

- Both rows state the same obligation, for the same actor, the same repository kind, and the same stage.
- The surviving id is the id that more tests name. If the tests tie, it is the id with more links, then the lower number.
- Each unique sentence of the row that goes is listed in the report. It moves to the surviving row.

## shorten

- Another row states each sentence that goes. Name that row.

## cover

- The `tests` number of the id is above 0.
- Each fact that leaves the row has an assertion in a test with that `id:`.
- The reason, the rejected alternative, and each rule across files stay.

## fix

- The finding is a contradiction or an against-code finding with a corrected sentence. A finding that is a question has no `fix` until the owner answered.
- Open the evidence, path and line, and read it. If the code now differs from the report, stop.
- For a contradiction, the row that is false is the row that the finding names. Search the board and the code once more for a third row that states the same false fact.
- The corrected sentence is true against the code, and it states no new fact that the code does not show.
- If the code is wrong and the row is right, stop. That is a task for `r-develop`. Change no code.

## delete

- The status of the file is `closed`.
- If no row states a reason of the file, the reason moves first. The report named the row. If it named none, stop.
