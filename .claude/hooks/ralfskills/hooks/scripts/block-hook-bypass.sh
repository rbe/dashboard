#!/bin/sh
# PreToolUse hook for Bash: refuse a Git command that skips the git hooks.
# The rule is R-127 of rbe/ralfskills.
#
# The pre-push hook refuses a push of content that make gates did not
# check. `git push --no-verify`, `git commit --no-verify`, and
# `git -c core.hooksPath=...` skip it. The owner may still use them in an
# own terminal. An agent runs make gates instead.

. "$(dirname "$0")/hook-command.sh"

command=$(read_hook_command) || exit 2

# Start of a command: line start, or a shell separator, then optional sudo.
start='(^|[;&|(]|&&|\|\|)[[:space:]]*(sudo[[:space:]]+)?'
# Git with optional -C <dir> and -c <key=value> options.
git='git([[:space:]]+-[Cc][[:space:]]+[^[:space:];&|]+)*[[:space:]]+'

no_verify="${start}${git}(push|commit)([[:space:]]+[^;&|[:space:]]+)*[[:space:]]+--no-verify([[:space:]]|$|[;&|)])"
hooks_path="${start}git([[:space:]]+-[Cc][[:space:]]+[^[:space:];&|]+)*[[:space:]]+-c[[:space:]]+core\.hooks[Pp]ath="

if printf '%s\n' "$command" | grep -Eq -e "$no_verify" -e "$hooks_path"; then
  deny 'This command skips the git hooks. The pre-push hook refuses a push of content that make gates did not check. Run make gates, then commit exactly the checked content and push. Rule R-127 of rbe/ralfskills.'
fi
exit 0
