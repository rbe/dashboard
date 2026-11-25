# Id kinds

- Roadmap row (work to do): one table row, id `W-` plus a number, from `W-1`. One id form serves the three kinds `feature`, `defect`, and `question`, because the column `kind` already holds the kind. A row is not done. `record` deletes it when the slice closes.
- Requirement row: one row of a file in `docs/requirements/`, id `R-` plus a number, from `R-1`. A repository with no `docs/adr/` gives the row a status: `planned` or `in force`.
- ADR: `docs/adr/<id>.md`, id `ADR-` plus four digits, from `ADR-0001`. The status is `Accepted` or `Superseded`.
- Proposal (the plan of one roadmap row): `docs/proposals/<id>.md`, id `P-` plus a number, from `P-1`. The status is `open`, `started`, or `done`.
- History file (a started slice): `docs/history/<id>.md`, id `H-` plus the day the file is created and a slug, as `H-2026-11-20-slugify`. The status is `started` or `closed`. The branch of the slice has the slug as its name.

## Counters

- `docs/ids.yaml` holds one counter for each kind that has a number: `R`, `W`, `ADR`, `P`, and any other kind that the repository already uses, such as `D`. One line is `R: 83`. The counter is the highest number issued.
- `make id KIND=<kind>` prints the next id of the kind and raises the counter by one. It creates `docs/ids.yaml` when the file does not exist. The counter only grows, so a deleted row or file never gives its number again.
- `make id-raise KIND=<kind> TO=<number>` sets a counter to a higher number, for a repository that already uses ids of that kind.
- An id is valid when its number is not above the counter of its kind. A history id has no counter. It must be unique among the files.
- `make ids` fails on a list item that is not an id, on an id above its counter, on the same live id twice, and on a counter below the highest live id of its kind.
