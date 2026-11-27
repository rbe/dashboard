#!/bin/sh
# The git pre-push hook. It refuses the push unless build/gates.ok holds
# the tree id of the working tree, that is, unless make gates passed after
# the last edit. Git's own `git push --no-verify` skips it.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd "$(git rev-parse --show-toplevel)"
if ! sh "$here/gates-stamp.sh" check 2>/dev/null; then
  printf '%s\n' "push refused: build/gates.ok is missing or stale. Run make gates." >&2
  exit 1
fi
