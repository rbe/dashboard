<!--
Local dashboard format. The running app stores your board in data/dashboard.md,
which stays on this machine and is not committed.

# Subject

## System name
id: system-name
summary: What this is for
note: Optional private note
task: Optional task
tags: one, two
env: prod

- [Console](https://example.com) role=console

Any extra "key: value" line becomes a grouping field.
-->

# Development

## TeamCity
id: teamcity
summary: Build server for the main projects
task: Operate
tags: ci, aoc
pinned: true
env: prod

- [Console](https://www.jetbrains.com/teamcity/) role=console
- [Docs](https://www.jetbrains.com/help/teamcity/getting-started.html) role=docs

## SonarQube
id: sonar
summary: Code quality
task: Review
tags: quality, aoc
env: prod

- [Docs](https://docs.sonarsource.com/sonarqube/latest/) role=docs

# Mail

## Webmail
id: webmail
summary: Read and send mail
task: Communicate
tags: mail

- [Roundcube](https://roundcube.net/) role=mail

# Reise

## Bahn
id: bahn
summary: Tickets and schedules
task: Book
tags: travel

- [Deutsche Bahn](https://www.bahn.de/) role=console
