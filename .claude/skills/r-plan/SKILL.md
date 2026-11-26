---
name: r-plan
description: Grills a change before editing. Use when a request is new, vague, or would change a rule, an ADR, the roadmap, or a proposal. A named source file, a failing test, or a defect row of the roadmap is r-develop.
---

The general rules in `CLAUDE.md` apply.

<purpose>
`r-plan` asks the owner until the slice is one sentence, names the boundary and the pattern, and records the answers before `r-develop` edits a file.
</purpose>

<steps>
1. Read the board: `docs/ROADMAP.md`, `docs/adr/index.toon`, `docs/requirements-index.toon`, `docs/skill-index.toon`, and the open files in `docs/proposals/`.
   If a file does not exist, skip it.
   For each row of `docs/requirements-index.toon` that names a part that the change touches, run `make req ID=<ids>`.
   If the index names an ADR that this slice can change, read that ADR.
2. For each row of `docs/skill-index.toon` with the `kind` `check`, in file order: read that skill and ask its questions.
   If the request is too vague for these questions, do step 3 first. Ask them when the slice is one sentence.
   Write the line with the answers, as `security: no listener, no secret.`
3. Ask the owner until the slice is one sentence with an out-of-scope line.
   Architectural patterns are part of these questions.
   Before the slice closes, ask what the result looks like: the output or the interface, the empty case, and the error case. `r-develop` cannot ask the owner later.
   Ask `r-record` for a roadmap row for each question that the owner has not answered.
   If a proposal has no answers, do steps 2 to 4 for it in full now. The proposal keeps its text.
4. Name the boundary and the pattern for this slice in one sentence: who owns state, and what may call what.
   If the boundary keeps the slice out of a package, name each existing function of that package that the slice needs. Say whether the slice moves it, exports it, or repeats it.
   If that sentence is missing, stop.
5. Evaluate architecture, scalability, and code quality against the constraints of this system. Prefer the smallest design that stays operable and maintainable.
   When a choice is expensive to reverse, name the options, recommend one, and wait. Otherwise implement it in small modules.
6. If the owner answers a choice that must hold, ask `r-record` where it goes: a requirement row, a sentence in an ADR, or a new ADR.
   A storage format, a protocol, and the interface of a library are expensive to reverse, so each is an ADR. The project is a library when the entry file says it ships as a library package.
   For a library interface, the ADR is the public names and their signatures. What a function does is requirement rows.
   A choice that need not hold is not recorded.
7. If the Makefile is missing, or if the slice adds or overrides a target, invoke `r-project-setup`.
8. If the slice needs a language and no `language` row of `docs/skill-index.toon` matches the files, stop. The index lists only installed skills.
9. If the owner chooses to implement now: create the branch of the slice with `git checkout -b <slug>` and ask `r-record` for a history file.
   Ask `r-record` to write the Plan section: the questions and answers, the boundary and the pattern, the lines of step 2, and each ADR id.
   Each answer that a test must prove becomes a requirement row, or an ADR as step 6 says. `r-develop` names those ids in the tests.
   Develop, Review, and Release read `Not invoked yet.`
10. If the owner chooses to implement later: ask `r-record` for a proposal id and write `docs/proposals/<id>.md`. Ask `r-record` for the roadmap row that names the proposal. Create no history file.
</steps>

<rules>
- Ask the owner one question at a time. Ask only what the code and the board do not answer.
- Do not ask a question that an accepted ADR, a requirement row in force, or an open proposal already answers.
- If the code or the board answers a question of step 2, write that answer in the line of that row.
- The roadmap row holds the kind, the title, and the proposal link. The questions and answers stay in the Plan section.
</rules>
