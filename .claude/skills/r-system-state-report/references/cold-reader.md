# The cold-reader check

You cannot find your own unclear terms, so an independent reader checks the report.

1. Give a subagent only the report: no code, no chat, no explanation.
2. Ask it to return each of these:
   - Each term that the report does not define and that is not a common word.
   - Each sentence that it can read in two ways.
   - Each statement without a source and a status.
   - Each sentence that breaks the communication contract or a rule of this skill.
   - For each item in "Decisions for you": whether it can select an option with only the report.
3. Correct each finding. If the first run had more than 5 findings, run the check again.

If you cannot start a subagent, read the report sentence by sentence against the glossary and the rules. Tell the user that no independent reader checked the report.
