# Indexes

## `make toon`

`make toon` writes `docs/requirements-index.toon` and `docs/skill-index.toon` in the skill collection, and `docs/adr/index.toon` and the skill index in a product repository.

| File | Columns | What it lists |
| --- | --- | --- |
| `docs/adr/index.toon` | `id`, `status`, `title`, `adrs`, `skills`, `roadmap` | ADR frontmatter. `r-plan` opens one ADR when the id matches |
| `docs/requirements-index.toon` | `id`, `title`, `status`, `file`, `owner` | The rows of `docs/requirements/`, when those files are the board and `docs/adr/` has no ADR file. The status is `planned` or `in force`. A row of a table with no status column is `in force`. The file is the path of the file of the row, and the owner is its name without `.md`. An agent runs `make req ID=<ids>` for the statement |
| `docs/skill-index.toon` | `name`, `kind`, `order`, `files`, `names`, `stages` | Installed skills whose frontmatter `kind` is `language` or `check`. `stages` lists the stage skills that load the skill |

- A repository that keeps `docs/requirements/` and no `docs/adr/` gets `docs/requirements-index.toon` and the skill index. `make toon` does not create `docs/adr/` there.
- A product repository with no ADR still gets an `docs/adr/index.toon` that holds only the header.
- If a repository has an ADR file and `docs/requirements/`, `make toon` writes the ADR index.
- `project.mk` and `sdlc.mk` include `.claude/skills/r-record/index.mk`. A Makefile that includes one of them has the targets `toon`, `ids`, `id`, `id-raise`, `req`, `links`, and `links-check`.
- `make setup` runs `toon` first when that include is present.
- `toon` and `ids` call `$(PYTHON)` from `r-project-setup`. `make ids` checks ids and writes no index.

## Skill index

- The skill index lists the installed set under `.claude/skills/`. In the skill collection, before install, it lists `skills/`.
- The index does not copy skill prose.
- A language skill sets `files` to extensions and `names` to exact filenames such as `Makefile`. `r-develop` invokes the language row whose `files` or `names` match the files in hand.
- A check skill sets `order`. `r-plan` and `r-review` follow that order.
- A skill sets `stages` in its frontmatter. A stage reads the rows whose `stages` names it, so no stage names a subskill or a language skill in its text. A product repository with an older skill has an empty `stages`, and no stage loads that row.

## Why `make toon` fails

- The `name` in the frontmatter of a skill differs from its directory.
- A frontmatter value has a colon followed by a space, or a space followed by `#`. APM reads the frontmatter as YAML and refuses to install such a skill.
