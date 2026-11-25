# The workflow, versioning, and retention

## Jobs

The job ids are `setup`, `build`, `test`, `docs` when the repository renders docs, `publish-container`, `publish-github` when the project releases a JAR, and `report`.

```
setup ──┬── build ──┬── publish-container ──┐
        ├── test ───┤                       ├── report
        │           └── publish-github ─────┤
        └── docs ───────────────────────────┘
```

- `test` runs beside `build`. The `test` job runs `make test`.
- `report` has `if: ${{ !cancelled() }}` and is the last job.
- `setup` runs `make cleanup-actions-artifacts` before it uploads.

## Triggers and permissions

- The triggers are `push` on every branch and `workflow_dispatch` with a `job` choice. There is no `pull_request` trigger and no tag trigger.
- The default branch is `github.event.repository.default_branch`.
- A manual publish also runs `build` and `test`, and it needs both to succeed.
- The workflow cancels a run in progress only when the push is not on the default branch.
- Permissions: `contents: read` at the top, `actions: write` on `setup`, `packages: write` on `publish-container`, `contents: write` on `publish-github`.
- The YAML contains no `./gradlew`, `npm`, `podman`, `python`, `tar`, `printf`, or `tee`. Gradle is `make build`. The registry login is `make login`.
- The workflow `env` holds `IMAGE` and `SDLC_DEFAULT_BRANCH`, which is `github.event.repository.default_branch`. The Makefile sets `IMAGE` to the same image name.
- The `env` of the Node template also holds `NODE_VERSION` at 24. A Gradle project uses the JDK of its template.
- The workflow pins one runner label, `ubuntu-26.04`.

## Artifacts and retention

All repositories of one account share the artifact quota, so each upload has a short retention.

- `retention-days` is 1 for an intermediate artifact, and 14 for `report` and rendered docs.
- Between jobs, pass the tested JAR or the image tar. Do not upload the workspace, a Gradle home, or a whole `build/` directory.
- Each job uploads `report-<job>` with `build/logs` and `build/summaries`. `test` also uploads the test results and `build/coverage`.
- The `report` job downloads `report-*` into `build/inputs` and runs `make report`. `build/report/index.md` is the entry point.
- `make cleanup-actions-artifacts` deletes every other artifact of the repository when it is one hour old. `report` and `docs` stay until their retention ends. The artifacts of the current run stay.

## Versioning

- `make version` runs `git describe --tags --abbrev=0 --match 'v[0-9]*'` and accepts only `vMAJOR.MINOR.PATCH`. If a pre-release tag such as `v1.2.0-rc.1` is nearer, the publish fails, also when an older release tag exists.
- In a shallow clone, `make version` fetches the tags one time.
- The published version is `MAJOR.MINOR.PATCH-<run>`. A publish from the default branch also tags `latest`. A manual publish from any other ref does not.
- There is no `edge` tag, no `sha-*` tag, and no bare `1.2.0` tag.
- After a push to the default branch, the cleanup keeps that run and the next-lower run number on the same `MAJOR.MINOR.PATCH` line. The upload time does not decide.
- The cleanup reads the published run from `PUBLISHED_TAG`, else from `build/publish-version.txt`. When both are empty, as on a laptop, it keeps the newest rolling version by `created_at`. It needs no git tag.
- The cleanup does not delete a GHCR version that carries `latest` or a tag other than `MAJOR.MINOR.PATCH-<run>`.
- HTTP 404 for a missing package is an empty list, so the first cleanup does not fail the job.

To publish a new version, the owner does these steps:

1. Tag the default branch with `vX.Y.Z`.
2. Push the tag.
3. Start `publish-container` on the Actions page of GitHub. The owner clicks it there. No command is typed.

A tag push does not publish. If it did, one commit would be published two times, and the cleanup would delete the real former version.
