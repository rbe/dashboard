#!/bin/sh
# PreToolUse hook for Bash: refuse an inline Python script that writes a file
# of the project.
#
# The pattern is read_text(), then replace(), then write_text(). It rebuilds
# the unique-match contract of the edit tool without its atomicity. In
# rbe/emailtodisk such a script wrote a module and then crashed on its check,
# so the module could not be imported. The edit tool fails before it writes.
#
# The hook refuses a Python command (python, python3, uv run python, or
# make py) when it has a write call and a quoted relative path, such as
# "src/app.py" or './docs/x.md'. A path under build/ and an absolute path,
# such as /tmp/x, pass. A Python command that only reads also passes.

. "$(dirname "$0")/hook-command.sh"

command=$(read_hook_command) || exit 2

has() {
  printf '%s\n' "$command" | grep -Eq "$1"
}

python='(^|[[:space:];&|(])(python3?|uv[[:space:]]+run[[:space:]]+python3?|make[[:space:]]+py)([[:space:]]|$)'
has "$python" || exit 0

# sys.stdout.write and sys.stderr.write print, so they are no file write.
command=$(printf '%s\n' "$command" | sed -E 's/std(out|err)\.write\(//g')

q="[\"']"
write="write_text\(|write_bytes\(|writelines\(|\.write\(|open\([^)]*${q}[wax]b?\+?${q}"
relative_path="${q}(\./)?[A-Za-z0-9_][A-Za-z0-9_.-]*/"
build_path="${q}(\./)?build/"

if has "$write" && has "$relative_path"; then
  # Each relative path names build/: the script writes build output only.
  others=$(printf '%s\n' "$command" | grep -Eo "$relative_path" | grep -Ev "$build_path")
  if [ -n "$others" ]; then
    deny 'This inline Python script writes a file of the project. Use the edit tool for a change, or the write tool for a new file. The edit tool fails before it writes when the old text is missing or occurs twice. A script can write and then crash with the change half done. A script that only reads files is allowed.'
  fi
fi
exit 0
