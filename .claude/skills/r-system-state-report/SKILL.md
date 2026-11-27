---
name: r-system-state-report
description: Writes a plain-language report on what an agent-built system does now, which decisions shaped it, and what the human must decide. Use for 'state report', 'what did we build', 'review the system'.
---

The general rules in `CLAUDE.md` apply.

<purpose>
The report lets a human check the state of a system that agents built through many chats, and decide the direction.
The report is successful if the reader understands each sentence on the first reading and can make each open decision without a question back.
</purpose>

<steps>
1. Collect the evidence. Read before you write. Write down each thing that you cannot read or run. It goes in the section "Not verified".
   - The repository: structure, entry points, configuration, tests.
   - The history: `git log`, and the diffs of the period that the user names. If the user names no period, use the time since the last report in `reports/`, or the full history.
   - The board, each file when it exists: `docs/ROADMAP.md`, the files in `docs/requirements/`, the ADRs in `docs/adr/`, and the history files in `docs/history/`.
   - `build/project-report.md`, after you run `make project-report`, when `r-project-report` is installed.
   - The current chat, and the transcripts or notes that the user supplies.
   - The result of `make test`, and of the target that `CLAUDE.md` names for starting the system. Run each only if it changes no data and no external system. Record the real result.
2. Read `docs/glossary.md` before you write the report.
   - List the things that the report must name: components, data, actors, processes.
   - Use the term that `docs/glossary.md` gives for each thing.
   - If a thing has no term, ask `r-record` to add its row before you write the report. If the file does not exist, `r-record` creates it.
3. Write the report in the language of the user. Use these sections in this order. If a section has no content, say so in one line.
   1. Summary. Maximum 5 sentences: what the system does now, the largest difference from what was asked, and the number of decisions that wait for the human.
   2. What the system does now. A list of behaviours that a person can observe, in the form "When [actor] does [action], the system does [result]." Do not list files or modules.
   3. Differences from what was asked. Each item: what was asked, with the source; what exists; the effect for the user.
   4. Choices that were made. A table: the choice; who made it (human, agent, or agent without a question to the human); the rejected alternative; the reason; whether it is easy to reverse; the board row (a requirement row, an ADR, or a roadmap row). Put the choices that an agent made without a question first. Write `none` as the board row of each choice that has no such row.
   5. Not verified. What you could not run or read, and what only a chat claims.
   6. Risks and defects. Only those that you can point to, each with the location and the effect.
   7. Decisions for you. Each item is a question that the human answers with a selection. Give the options, the effect of each option, and your recommendation with one reason.
   8. Glossary. Copy the rows of `docs/glossary.md` for each term that the report uses. The reader of the report then needs no other file.
4. Read `references/cold-reader.md` and run the cold-reader check.
5. Save the report as `reports/state-YYYY-MM-DD.md`. `make links` reads only `docs/`, so write each id in the report as a link by hand.
6. For each choice with the board row `none` that must hold, ask `r-record` where it goes. A decision that need not hold gets no row. For each defect of section 6 and each question of section 7, ask `r-record` for a roadmap row of the kind `defect` or `question`.
7. In the chat, give the summary, the list "Decisions for you", and the rows that `r-record` added. Do not repeat the full report.
</steps>

<rules>
- Do not describe a file that you did not open.
- Each statement in sections 2 to 6 has a source and a status. If a statement has no source, delete it.
- A source is `path/to/file:line`, a commit hash, a test name, or a chat passage with a date or a short quote.
- A status is one of three words. "ran": you executed it in this session and saw the result. "read": you read it in the code and did not execute it. "said": only a chat or a commit message states it. Do not change "read" or "said" into "ran".
- Use present tense for the current state. Use past tense only for events.
- These words are judging words: robust, clean, seamless, simple, powerful, improved, optimized, comprehensive.
- A noun chain has at most 3 nouns. In German, break a long compound with a hyphen or rewrite it.
- Use a list for parallel items, a table for a comparison, and sentences for cause and effect.
- Change no file other than the report and the rows that `r-record` writes. Do not add a second instruction file: `CLAUDE.md` tells each agent where a decision goes.
</rules>

<example>
The import job tries a failed write 3 times. Status: read. Source: `db/orders.py:41`.
</example>

<references>
- `references/cold-reader.md`: the cold-reader check of step 4. Read it in step 4.
</references>
