# Pipeline rules

The rules of the pipeline stand once, in the skills `r-project-setup` (the Make contract) and `r-github-pipeline` (the GitHub contract, the publish rules with `AUTO_PUBLISH`, versions, cleanup, and retention). This file does not repeat them. It holds only the facts of this repository and its divergences.

## This repository

Replace each bracket with a fact of this repository.

| | |
| --- | --- |
| Image | `ghcr.io/[owner]/[name]` |
| Default branch | [the default branch] |
| Toolchain | [the toolchain and the image of this project] |

## Divergences

Each entry names the shared rule, what differs, and why. A toolchain difference belongs here.

- Rule: [the shared rule]. Here: [what differs]. Why: [the reason].
