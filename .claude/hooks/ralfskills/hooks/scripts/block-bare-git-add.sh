#!/bin/sh
# PreToolUse hook for Bash: refuse a Git command that stages the whole
# working copy. The rule is R-114 of rbe/ralfskills.
#
# A working copy can hold files that must never enter history: personal data,
# secrets, exports, build output. `git add -A`, `git add .`, `git add -u`,
# `git add :/`, and `git commit -a` stage every changed file. A pathspec bounds
# the command, so `git add -A src/ tests/` passes.

. "$(dirname "$0")/hook-command.sh"

command=$(read_hook_command) || exit 2

# Start of a command: line start, or a shell separator, then optional sudo.
start='(^|[;&|(]|&&|\|\|)[[:space:]]*(sudo[[:space:]]+)?'
# Git with optional -C <dir> and -c <key=value> options.
git='git([[:space:]]+-[Cc][[:space:]]+[^[:space:];&|]+)*[[:space:]]+'
# End of the command: line end or a shell separator.
end='[[:space:]]*($|[;&|)])'

bare_add="${start}${git}add([[:space:]]+(-A|--all|-u|--update|--|\.|\./|:/))+${end}"
commit_all="${start}${git}commit([[:space:]]+[^;&|[:space:]]+)*[[:space:]]+(-[A-Za-z]*a[A-Za-z]*|--all)([[:space:]]|$|[;&|)])"

if printf '%s\n' "$command" | grep -Eq -e "$bare_add" -e "$commit_all"; then
  deny 'This command stages the whole working copy. The working copy can hold files that must not enter history, such as personal data, secrets, or exports. Stage the files of the change by name, for example git add src/ tests/. A pathspec bounds the command, so git add -A src/ is allowed. Rule R-114 of rbe/ralfskills.'
fi
exit 0
