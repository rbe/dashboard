# ADRs

## When

- `r-plan` says when a choice is an ADR. `r-record` writes `docs/adr/<id>.md` with the status `Accepted`. The Plan section of the history file cites that id.

## Where a choice goes

Not every choice is a rule. When a choice must hold, `r-record` decides where it goes, in this order:

1. A small requirement: a row of the file of its owner in `docs/requirements/`, where the repository keeps those files. The owner is the skill of the sentence `<skill> owns ...`, and `collection.md` holds a row with no owning skill. A repository with no `docs/adr/` has only this home. A product with `docs/adr/` keeps no such files, so it has homes 2 and 3. Do not create the files in a product.
2. A sentence in an ADR that already fits.
3. A new ADR.

If no home fits, the agent asks the user. A choice that need not hold has no home and is not recorded.

## Body

- `## Rule`: what an agent must do or must not do, in sentences that `r-review` can check.
- `## Why`: the reason, and the options that were not chosen.
- `## Divergence`: only in an ADR that replaces a skill rule. A pipeline divergence goes where `r-github-pipeline` says, and every other divergence is an ADR.
- Keep the ADR short. Do not copy the grill.

## Frontmatter

- An ADR file has no `version` key and no `date` key. Git holds both.
- The `status` is `Accepted` or `Superseded`. The same holds for `template.md` of `docs/adr/`.
- `make ids` fails on a break of these rules.

## Status

- `r-record` owns the status.
- A new ADR names the ADR it replaces in `supersedes`. `r-record` then sets the status of the replaced ADR to `Superseded`.
- The project report does not list a superseded ADR as an id with no test.

## `skills`

- `skills` names each skill whose work the ADR governs. Each name is an installed skill: a stage, a language skill, or a subskill.
- A rule for every change names the two stages that every slice uses: `skills: [r-develop, r-review]`.
- A rule for one language names that language skill too: `skills: [r-python, r-develop, r-review]`.
- An ADR with an empty `skills` list has no reader. Do not write one.
