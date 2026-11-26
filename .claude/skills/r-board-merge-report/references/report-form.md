# Report form

The first sentence of the reply states the intent. A short count follows: the findings of each kind and the contradictions.

## Tables

| Kind | Columns |
| --- | --- |
| Merge | No, Ids, Repeated text, Words now, Words after, Sentences to move, Tests to rewrite, Links to rewrite, Survives |
| Shorten | No, Ids, Repeated text, Words now, Words after, Kept in |
| Covered by code | No, Ids, Facts the tests pin, Words now, Words after, Kept in the row |
| Delete history | No, Ids, Words now, Words after, Reason to move first, Links to remove |
| Contradiction | No, Ids, Quote of each side, Evidence (path and line), False row, Corrected sentence or Question and choices |
| Against code | No, Id, Quote, Evidence (path and line), Corrected sentence or Question and choices, Fix (row edit or task for `r-develop`) |

- The numbers continue across the tables, so that each finding has one number.
- Words now is the sum of the rows. Words after is about, and it is your estimate. For a deletion it is the words of the sentence that moves.
- Tests to rewrite and Links to rewrite are the numbers of the id that goes. Links to rewrite leave out history files. Name the tests to rewrite as `file::name`, as the column `names` of `make board-numbers` gives them.
- Facts the tests pin names the tests that pin them, as `file::name`.
- Sentences to move are a quote, or none.
- The repeated text is a quote of at most 20 words.
- A contradiction or an against-code finding with a question has no corrected sentence. The owner answers first.

## Sample

Invented, for the form only.

| No | Ids | Repeated text | Words now | Words after | Sentences to move | Tests to rewrite | Links to rewrite | Survives |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | R-51, R-76 | "a skill states only what it adds" | 338 | about 300 | none | 2 | 4 | R-76 |

## Last lines

- To choose, write the action and the ids: `merge R-51 R-76`, `shorten R-12`, `cover R-40`, `delete H-2026-11-15-slug`, `fix R-12`.
- A question has no action line until the owner answers.
- Say that the report can age, and that `r-board-merge` checks each finding again.
