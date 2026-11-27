# Setup mode: cases

## A command variable

Step 3 reads this section before it sets a command variable, and when a recipe runs a tool on the host.

- Set a variable only if it is empty and the toolchain is already in the project (`package.json`, Gradle, python, or tar). A value that the project set stays.
- If the Makefile already has a recipe for a target, leave the recipe and leave the command variable empty. The report names that variable as missing.
- If a recipe runs Gradle, npm, node, python, or go on the host, rewrite it to the command variable and keep what it does. The command of the template replaces a host recipe that runs the same tests or the same build. A target with no command variable, such as `run`, keeps its name and its place after the include. Its recipe uses `$(PYTHON)`, `$(NODE)`, `$(GRADLE)`, or `$(GO)`.
- If the project has no dependency to resolve, no artifact to build, or no integration entry, set that command to `true`.
- If the project ships a binary or a library package, set what the language skill names for it, such as `BIN` for Go, or set `BUILD_CMD`. Then `make build` writes the shipment from the first run.
- If the repository renders docs, set `RENDER_DOCS`, and `DOCS_OPTIONS` if the pages need options. Delete the project's own renderer. If an image is published, set `PUBLISH_IMAGE`.

## An existing `CLAUDE.md`

Step 7 reads this section when the file exists.

- Add each paragraph of the template that is missing. Keep its other text, except as the last bullet says.
- If the file has no line `@.claude/skills/r-project-setup/rules.md`, add the last paragraph and that line of the template at the end of the file.
- Delete each copy of the sections `## General rules`, `## Agents`, and `## Communication contract`, and each other sentence that `rules.md` states. Name each deleted sentence in the reply.

## A test with no id

Step 8 reads this section when a test has no `id:` line.

- Find the test with `make project-report` when that skill is installed.
- Ask `r-record` where the behaviour that the test proves goes, as a requirement row or an ADR, and name that id in the test. One row can serve several tests.
