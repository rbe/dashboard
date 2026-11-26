# Shared part of the guard hooks. Sourced, not run.
#
# read_hook_command reads the hook input (JSON) from stdin and prints the
# value of tool_input.command, with the JSON escapes resolved. It needs only
# POSIX awk, so the host needs no jq. If the input has no command, it prints
# a message to stderr and exits 2. A PreToolUse hook that exits 2 blocks the
# command and shows the message, so a changed input format fails loudly.

read_hook_command() {
  awk '
    { input = input $0 " " }
    END {
      if (!match(input, /[{,][ \t]*"command"[ \t]*:[ \t]*"([^"\\]|\\.)*"/)) {
        exit 1
      }
      value = substr(input, RSTART, RLENGTH)
      sub(/^[{,][ \t]*"command"[ \t]*:[ \t]*"/, "", value)
      sub(/"$/, "", value)
      gsub(/\\\\/, "\001", value)
      gsub(/\\"/, "\"", value)
      gsub(/\\n/, "\n", value)
      gsub(/\\t/, "\t", value)
      gsub(/\\\//, "/", value)
      gsub(/\\u0027/, "\047", value)
      gsub(/\\u0026/, "\\&", value)
      gsub(/\\u003[cC]/, "<", value)
      gsub(/\\u003[eE]/, ">", value)
      gsub(/\001/, "\\", value)
      printf "%s", value
    }
  ' || {
    echo "Guard hook $0: the hook input has no tool_input.command. The hook blocks the command." >&2
    exit 2
  }
}

# deny prints the PreToolUse answer that refuses the command with a reason.
# The reason must not contain a double quote or a backslash.
deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
}
