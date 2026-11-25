#!/usr/bin/env python3
"""Print the requirement rows and the ADRs that a question needs, and no more.

make req ID="R-45 R-75" prints each named item in full.
make req Q=podman prints id, title, and file of each item whose title or
statement holds the word, and with FULL=1 the statement too.
make req OWNER=record and make req STATUS=planned list the rows of one owner
or one status. A filter combines with the others.

The items are the rows of docs/requirements/<owner>.md and the ADRs of
docs/adr/. An ADR has no owner, so a filter by owner lists rows only. An ADR
holds its text after the frontmatter.
"""

import argparse
import sys
from pathlib import Path


def sibling(name):
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    return __import__(name)


def adr_items(root):
    """Each ADR as id, title, status, file, owner (empty), and statement."""
    adr_index = sibling("adr_index")
    found = []
    folder = root / "docs" / "adr"
    paths = sorted(folder.glob("*.md")) if folder.is_dir() else []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        data = adr_index.frontmatter(text)
        if "id" not in data:
            continue
        end = text.find("\n---", 3) if text.startswith("---") else -1
        body = text[end + 4 :].strip() if end >= 0 else text.strip()
        found.append(
            {
                "id": data["id"],
                "title": str(data.get("title", "")),
                "status": str(data.get("status", "")),
                "file": path.relative_to(root).as_posix(),
                "owner": "",
                "statement": body,
            }
        )
    return found


def items(root):
    return sibling("requirements_index").rows(root) + adr_items(root)


def holds(item, word):
    needle = word.lower()
    return needle in item["title"].lower() or needle in item["statement"].lower()


def select(found, word="", owner="", status=""):
    """The items that pass every filter that is set."""
    chosen = []
    for item in found:
        if word and not holds(item, word):
            continue
        if owner and item["owner"] != owner:
            continue
        if status and item["status"].lower() != status.lower():
            continue
        chosen.append(item)
    return chosen


def full_text(item):
    lines = [item["id"]]
    for key in ("title", "status", "file", "owner", "statement"):
        if item[key] or key != "owner":
            lines.append(f"{key}: {item[key]}")
    return "\n".join(lines)


def list_line(item, full):
    line = f"{item['id']} | {item['title']} | {item['file']}"
    return f"{line}\n  {item['statement']}" if full else line


def by_ids(found, wanted):
    """The items of the wanted ids in the wanted order, and the ids not found."""
    index = {item["id"]: item for item in found}
    chosen = [index[ident] for ident in wanted if ident in index]
    missing = [ident for ident in wanted if ident not in index]
    return chosen, missing


def run(root, ids="", word="", owner="", status="", full=False):
    """The text to print, the messages for stderr, and the exit status."""
    found = items(root)
    if ids:
        if word or owner or status:
            return "", ["req: set ID alone, or set Q, OWNER, or STATUS"], 2
        chosen, missing = by_ids(found, ids.replace(",", " ").split())
        text = "\n\n".join(full_text(item) for item in chosen)
        return (
            text,
            [f"req: {ident} not found" for ident in missing],
            (1 if missing else 0),
        )
    if not (word or owner or status):
        return "", ["req: set ID, Q, OWNER, or STATUS"], 2
    chosen = select(found, word, owner, status)
    if not chosen:
        return "", ["req: no item matches"], 1
    return "\n".join(list_line(item, full) for item in chosen), [], 0


def main(argv):
    parser = argparse.ArgumentParser(prog="req.py")
    parser.add_argument("--id", default="")
    parser.add_argument("--q", default="")
    parser.add_argument("--owner", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args(argv[1:])
    root = sibling("requirements_index").repo_root(Path.cwd())
    text, errors, code = run(root, args.id, args.q, args.owner, args.status, args.full)
    if text:
        print(text)
    for error in errors:
        print(error, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
