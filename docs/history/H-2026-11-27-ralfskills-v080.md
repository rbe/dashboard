---
id: H-2026-11-27-ralfskills-v080
title: Move to RalfSkills 4c028a8
status: closed
adrs: []
skills: [r-plan, r-develop, r-review, r-record]
roadmap: []
proposals: []
---

# Move to RalfSkills 4c028a8

## Plan

The owner asked to move dashboard to RalfSkills commit 4c028a8, the future v0.8.0. The owner chose to delete the project renderer and `scripts/workflows.test.mjs`.

## Develop

`apm.yml` pins the commit and no longer lists `r-upgrade-node-components`. APM reinstalled `.claude/skills`. The Makefile has no `DOCS_CMD`, so `make docs` uses the shared renderer. Deleted: `scripts/render-docs.mjs`, `scripts/render-docs.test.mjs`, `scripts/workflows.test.mjs`. `CLAUDE.md`, `ADR-0004`, `README.md`, `.npmignore`, and `.prettierignore` no longer name them. The README names the two-architecture image.

## Review

`make editorconfig`, `format`, `lint`, `test`, `integration`, `coverage`, `check-docs`, and `docs` passed. `make ids` and `make links-check` passed. No finding.

## Release

Not invoked: the owner merges the pull request.
