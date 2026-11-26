---
name: r-skills-review
description: Reports where installed skills overlap, which rule two places state, which action two skills do, and which statements contradict. Writes nothing. Use when the owner asks to find skill overlaps, to cut duplicate skill text, or to check the skills against CLAUDE.md.
---

The general rules in `CLAUDE.md` apply.

<purpose>
The report lists skill text that states one rule twice, lets two skills do one action, or says opposite facts. The owner reads it once and decides who owns each rule. This skill covers skill files only. `r-board-merge-report` covers the board documents in `docs/`.
</purpose>

<inputs>
- The scope is each `SKILL.md` and each file under `references/` of the installed skills, and the general rules and the communication contract of `CLAUDE.md`.
- In this collection the installed skills are the folders `skills/r-*/`. In a project they are the folders `.claude/skills/*/`, with each project skill such as `orgme-plan`.
- Scripts, templates, and makefiles of a skill are out of scope. Read them only as evidence for a contradiction.
</inputs>

<steps>
1. List the installed skills. Read the general rules and the communication contract of `CLAUDE.md`.
2. Read each `SKILL.md` and each file under `references/` in full. Note the number of each line that states a rule or does an action.
3. List the candidates of the three kinds. Read `references/finding-kinds.md` for the test of each kind.
4. Try to refute each candidate. Drop a pointer, and drop a statement that differs in actor, condition, or stage.
5. For each finding that stays, name the owner by the owner rule.
6. Write the report as the output says.
</steps>

<rules>
- A pointer is not an overlap. `invoke r-record`, `see references/x.md`, and a name of another skill are pointers.
- The owner rule: a rule that the general rules of `CLAUDE.md` state stays only there. Any other rule belongs to the skill whose purpose names the subject. The other places keep a pointer.
- If two skills have a purpose that names the subject, the owner is a question to the owner of the collection. List the choices.
- A contradiction needs both quotes. Say which side the owner rule or the code supports. If neither decides, the finding is a question.
- Write each place as `path:line` and quote at most 20 words.
- Change no file. A fix is a task for `r-develop`.
</rules>

<output>
- The first sentence of the reply states the intent. A count follows: the findings of each kind and the number of files read.
- One table for each kind: Same rule in two places, Same action in two skills, Contradiction. A kind with none gets one line that says none.
- Each finding has a number, the kind, each place as `path:line`, a short quote, and the proposed owner. The numbers continue across the tables.
- A contradiction adds the side that holds and the reason.
- The reply names the files that you did not read.
</output>

<references>
- `references/finding-kinds.md`: the test of each finding kind and what is not a finding. Read it in steps 3 and 4.
</references>
