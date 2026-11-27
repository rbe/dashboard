#!/bin/sh
# Prints the id of the tree object of the working tree: every tracked
# file and every untracked file that git does not ignore, outside build/.
# It works on a copy of the index in a temporary file, so the real index
# and the staging area stay as they are. After a commit of exactly this
# content, the id equals the tree of that commit, so a stamp survives it.
set -eu
tmp=$(mktemp -d)
trap 'rm -f "$tmp/index"; rmdir "$tmp"' EXIT HUP INT TERM
index=$(git rev-parse --git-path index)
if [ -f "$index" ]; then cp "$index" "$tmp/index"; fi
export GIT_INDEX_FILE="$tmp/index"
git ls-files -z --cached --others --exclude-standard -- . ':!build/' |
  git update-index --add --remove -z --stdin
git write-tree
