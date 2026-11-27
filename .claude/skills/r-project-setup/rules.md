## General rules

A skill states only what it adds to these rules.

<general_rules>

Interface:

- Type only `make <target>` and Git commands. A typed tool of POSIX `sh`, such as `tail` or `grep`, may only shorten or search output, and writes no file. Make runs every other tool in a Podman image, on this machine and in CI. The host needs only Make, Git, and Podman. Push only with a remote `origin`.
- If no target runs a command that the work needs, `r-project-setup` adds the target.
- Report mode writes nothing and fills its skeleton in the reply. Setup mode writes only what is missing or off the contract. A request for both runs report mode first.

Start of a task:

- Run `make old-board` before the first skill. If the target fails, the only skill is `r-migrate-docs`.
- If a step says stop, or needs a skill that is not installed, take no later step. Tell the user the step, the reason, and the missing skill.

Board:

- `r-record` writes every id and every board document. Invoke `r-record` before you create one.
- An architecture decision record (ADR) in `docs/adr/` is an architecture or development rule. An ADR with the status `Accepted` is a rule for every change.
- If the repository keeps `docs/requirements/` and no `docs/adr/`, a row of those files replaces an ADR, and a planned row replaces a roadmap row. Where a step names `docs/adr/index.toon`, read `docs/requirements-index.toon` in such a repository. For each row that names a part that the change touches, run `make req ID=<ids>`.
- Write one line for each `check` row of `docs/skill-index.toon`, or `checks: none installed`. For a subskill that is not installed, write `<name>: not installed`. A row without a line fails the step.
- Run `make toon` before you read an index. Hand-editing a file that a Make target writes is a defect.

Gates:

- The gates are `make editorconfig`, `make format`, `make lint`, `make test`, `make integration`, and `make coverage`. CI runs the same six targets.
- A change is done when `make gates` passed after the last edit. `r-review` runs it once, and the pre-push hook checks its stamp. Report a gate that did not run as not run, and why.
- A test names the ADR id or the requirement id that it proves in a line `id:`. Stop when a test has no id.
- Do not weaken a test, skip a test, catch an error silently, or put a secret or personal data in a fixture.
- A method does one thing or only composes other methods. Name each unit, function, method, class, and file from the domain.

</general_rules>

## Agents

A strong model, Fable or Opus, discusses, plans, orchestrates, and reviews. Sonnet implements normal work. Haiku implements mechanical work. Each brief names the files the agent owns and the check that accepts the work. The reviewing model runs the checks itself and re-checks each claim of an agent. If a Sonnet agent fails twice on one step, the orchestrator takes over or asks the owner, and the history file names the escalation. A skill file names no model and has no `model:` field. An agent file in `.claude/agents/` names a model alias.

## Communication contract

The user reads each reply once, often after a break, has not read the code, remembers no earlier chat, and decides from what you write.

Names:

- Use the user's words and the identifiers of the project, one name for one thing. Invent no synonym.
- Replace each label you invented with the project name or a description, or define it at its first use.
- Define an abbreviation at its first use.

Sentences:

- The first sentence states the understood intent. Stop when it is wrong.
- One statement per sentence. Maximum 25 words.
- Use active voice with a named actor.
- Put the condition before the result.
- Use full sentences, not arrows, symbols, or note style.

Content:

- Use the specific noun, number, path, or name.
- For "better", say what changed and what the effect is. Use no judging word without a measure.
- Say how you know each statement about the system: you ran it, you read it in the code, or you only assume it.
- Use literal language, not figures of speech.

Questions:

- Before a question, give the context: what the item is, what holds now, the choices, and the effect of each choice. Recommend one choice.
- Never write a bare id. Write each id with its title and as a Markdown link to its definition. `make req ID=<ids>` prints the title and the file.
- The user can answer without opening a file.

Example. Not: "Improved the persistence layer." But: "`save_order` in `db/orders.py` now tries a failed write 3 times. Before, one failed write stopped the import. I read this in the code. I did not run it."

These rules apply to what you write to the user, not to code, quotes, or a text for a different reader.

English follows ASD-STE100. German follows "Deutsch für die Technische Kommunikation" (tekom Deutschland e.V.). Name the standards. Copy no text of them. Keep German and English separate.
