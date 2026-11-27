#!/bin/sh
# gates-stamp.sh write   stores the tree id of the working tree in build/gates.ok.
# gates-stamp.sh check   exits 1 when the stamp is missing or differs.
# make gates calls write after the six gates passed. pre-push.sh calls check.
set -eu
here=$(dirname "$0")
stamp=build/gates.ok
current=$(sh "$here/tree-hash.sh")
case "${1:-}" in
write)
  mkdir -p build
  printf '%s\n' "$current" > "$stamp"
  ;;
check)
  [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$current" ]
  ;;
*)
  printf '%s\n' "usage: gates-stamp.sh write|check" >&2
  exit 2
  ;;
esac
