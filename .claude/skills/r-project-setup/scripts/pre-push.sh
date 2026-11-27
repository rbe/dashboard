#!/bin/sh
# The git pre-push hook. Git writes one line for each pushed ref to stdin:
#   <local ref> <local sha> <remote ref> <remote sha>
# For a pushed branch, the hook compares the tree of the pushed commit with
# the tree id in build/gates.ok, which make gates writes. It accepts the
# push when the two trees are equal, or when they differ only in board
# files (BOARD_FILES), such as the close commit of r-release. For a pushed
# v* tag, it runs make check-tag when the Makefile has that target. A
# deleted ref and another tag pass. Git's own `git push --no-verify` skips
# the hook.
set -eu
cd "$(git rev-parse --show-toplevel)"
board_files=${BOARD_FILES:-docs/history/ docs/ROADMAP.md docs/proposals/}
stamp_file=build/gates.ok

refuse() {
  printf 'push refused: %s\n' "$1" >&2
  exit 1
}

# is_board_file prints nothing and succeeds when the path is a board file.
# A board path that ends in / is a directory.
is_board_file() {
  for board in $board_files; do
    case "$board" in
    */) case "$1" in "$board"*) return 0 ;; esac ;;
    *) [ "$1" = "$board" ] && return 0 ;;
    esac
  done
  return 1
}

check_branch() {
  pushed_tree=$(git rev-parse "$1^{tree}")
  [ -f "$stamp_file" ] || refuse "$stamp_file is missing. Run make gates."
  stamp=$(cat "$stamp_file")
  [ "$pushed_tree" = "$stamp" ] && return 0
  git cat-file -e "$stamp^{tree}" 2>/dev/null ||
    refuse "$stamp_file names a tree that git no longer has. Run make gates."
  others=$(git diff-tree -r --name-only "$stamp" "$pushed_tree" | while IFS= read -r path; do
    is_board_file "$path" || printf '%s\n' "$path"
  done)
  [ -z "$others" ] && return 0
  printf '%s\n' "push refused: the pushed commit differs from the content that make gates checked. Files that are not board files:" >&2
  printf '%s\n' "$others" | head -n 5 | sed 's/^/  /' >&2
  refuse "commit exactly the content that make gates checked, or run make gates again."
}

check_tag() {
  if make -n check-tag TAG=v0.0.0 >/dev/null 2>&1; then
    make --no-print-directory check-tag TAG="$1" PUSHED="$2" ||
      refuse "make check-tag refused the tag $1."
  fi
}

while read -r local_ref local_sha remote_ref remote_sha; do
  # A sha of zeros only is a deleted ref.
  case "$local_sha" in *[!0]*) ;; *) continue ;; esac
  case "$remote_ref" in
  refs/tags/v*) check_tag "${remote_ref#refs/tags/}" "$local_sha" ;;
  refs/tags/*) ;;
  *) check_branch "$local_sha" ;;
  esac
done
exit 0
