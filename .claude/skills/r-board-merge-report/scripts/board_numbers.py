#!/usr/bin/env python3
"""Count the words, the tests, and the links of each board unit, and name the tests.

A unit is an in force requirement row, an ADR, or a history file. A planned
row is out of scope. The numbers are the base of the merge report. The agent
does not count.
"""

import re
import sys
from pathlib import Path

ID = r"(?:ADR-\d{4}|H-\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]-\d+)"
WHOLE = re.compile(ID)
ANCHOR = re.compile(r'<a id="[^"]*"></a>')
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
ID_LINK = re.compile(rf"\[({ID})\]\([^)\s]*\)")
LIST_LINE = re.compile(r"^[a-z]+:\s*\[(.*)\]\s*$")
TEST_ID = re.compile(rf"^(?:\"\"\"|'''|//+|/\*+|\*|#)?\s*id:\s*[\"']?({ID})")
SKIP = {
    ".git",
    ".claude",
    ".gradle",
    ".venv",
    "__pycache__",
    "apm_modules",
    "build",
    "dist",
    "docs",
    "node_modules",
}
OTHER_TEST_FILE = re.compile(
    r"(?:\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)"
    r"|(?:Test|Tests|Spec|IT)\.(?:java|groovy|kt)"
    r"|_test\.go)$"
)
DECLARATION = re.compile(
    r"\bdef\s+(\w+)\s*\("
    r"|\bfunc\s+(Test\w*)\s*\("
    r"|\b(?:void|fun)\s+(\w+)\s*\("
    r"|\b(?:it|test)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]"
)
COLUMNS = ("id", "kind", "status", "words", "tests", "links", "lists", "names")


def repo_root(start):
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir():
            return candidate
    return current


def plain(text):
    """The text without anchors and without the target of a link."""
    return LINK.sub(r"\1", ANCHOR.sub("", text))


def word_count(text):
    return len(plain(text).split())


def split_front(text):
    """The frontmatter lines and the body lines of a Markdown file."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], lines[index + 1 :]
    return [], lines


def scalars(front):
    data = {}
    for line in front:
        if ":" in line and line[:1] not in (" ", "-", "#"):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("'\"")
    return data


def table_rows(path):
    """Each table row of a file as (line number, id, cells after the id)."""
    found = []
    if not path.is_file():
        return found
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [part.strip() for part in stripped.strip("|").split("|")]
        ident = ANCHOR.sub("", cells[0]).strip()
        if WHOLE.fullmatch(ident):
            found.append((number, ident, cells[1:]))
    return found


def unit(ident, kind, status, words, path, line=0):
    return {
        "id": ident,
        "kind": kind,
        "status": status,
        "words": words,
        "path": path,
        "line": line,
    }


def status_index(path):
    """The place of the column Status among the cells after the id, or None."""
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [part.strip().lower() for part in line.strip().strip("|").split("|")]
        if cells[0] == "id":
            return cells.index("status") - 1 if "status" in cells else None
    return None


def row_units(root):
    found = []
    folder = root / "docs" / "requirements"
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        at = status_index(path)
        for number, ident, cells in table_rows(path):
            status = cells[at] if at is not None else "in force"
            if status == "planned":
                continue
            rest = [cell for index, cell in enumerate(cells) if index != at]
            words = word_count(" ".join(rest))
            found.append(unit(ident, "requirement", status, words, path, number))
    return found


def file_units(root):
    found = []
    for folder, kind in (("adr", "adr"), ("history", "history")):
        for path in sorted((root / "docs" / folder).glob("*.md")):
            front, body = split_front(path.read_text(encoding="utf-8"))
            data = scalars(front)
            ident = data.get("id", "")
            if WHOLE.fullmatch(ident):
                words = word_count("\n".join(body))
                found.append(unit(ident, kind, data.get("status", ""), words, path))
    return found


def units(root):
    return row_units(root) + file_units(root)


def test_files(root):
    found = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).parts
        if any(part in SKIP for part in relative) or not path.is_file():
            continue
        name = path.name
        if (
            (name.startswith("test_") and name.endswith(".py"))
            or name.endswith("_test.py")
            or OTHER_TEST_FILE.search(name)
        ):
            found.append(path)
    return found


def declared_name(lines, index):
    """The name of the test that the line `id:` at `index` belongs to.

    If the line is a comment, a declaration within the 3 lines below wins,
    because a comment above a test names that test. Else the nearest
    declaration above wins, because a docstring inside a test follows its
    declaration. Else the nearest one below is taken. The result is empty
    when the file has no declaration.
    """
    below = range(index + 1, len(lines))
    is_comment = not lines[index].strip().startswith(('"""', "'''"))
    near = below[:3] if is_comment else []
    for number in [*near, *range(index, -1, -1), *below]:
        match = DECLARATION.search(lines[number])
        if match:
            return next(group for group in match.groups() if group)
    return ""


def test_names(root):
    """The tests of each id as `file::name`, from the lines `id:`, sorted."""
    names = {}
    for path in test_files(root):
        label = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = TEST_ID.match(line.strip())
            if match:
                name = declared_name(lines, index)
                names.setdefault(match.group(1), []).append(
                    f"{label}::{name}" if name else label
                )
    return {ident: sorted(found) for ident, found in names.items()}


def mentions(root):
    """Each link and each frontmatter list item that names an id.

    Each mention is (id, file, line number, kind), the kind is link or list.
    A frontmatter list of a history file counts, because it names an id
    that the slice wrote or proved. A link in the text of a history file
    does not count, because the text keeps the ids that were deleted later.
    """
    found = []
    for path in sorted((root / "docs").rglob("*.md")):
        is_history = "history" in path.relative_to(root / "docs").parts[:-1]
        text = path.read_text(encoding="utf-8")
        front, _ = split_front(text)
        for number, line in enumerate(text.splitlines(), 1):
            in_front = number <= len(front) + 1
            if in_front:
                match = LIST_LINE.match(line.strip())
                for item in match.group(1).split(",") if match else []:
                    if WHOLE.fullmatch(item.strip().strip("'\"")):
                        found.append((item.strip().strip("'\""), path, number, "list"))
                continue
            if is_history:
                continue
            for match in ID_LINK.finditer(line):
                found.append((match.group(1), path, number, "link"))
    return found


def counted(item, kind, found):
    """The mentions of one unit that come from another document or row."""
    total = 0
    for ident, path, number, mention in found:
        if ident != item["id"] or mention != kind:
            continue
        if path == item["path"] and (not item["line"] or number == item["line"]):
            continue
        total += 1
    return total


def numbers(root):
    tests = test_names(root)
    found = mentions(root)
    rows = []
    for item in units(root):
        named = tests.get(item["id"], [])
        rows.append(
            {
                **item,
                "tests": len(named),
                "names": ";".join(named),
                "links": counted(item, "link", found),
                "lists": counted(item, "list", found),
            }
        )
    return rows


def cell(value):
    text = str(value)
    if any(character in text for character in ',"\n'):
        return '"' + text.replace('"', '""') + '"'
    return text


def render(rows):
    lines = [f"board[{len(rows)}]{{{','.join(COLUMNS)}}}:"]
    for row in rows:
        lines.append("  " + ",".join(cell(row[name]) for name in COLUMNS))
    words = sum(row["words"] for row in rows)
    lines.append(f"total: {len(rows)} units, {words} words")
    return "\n".join(lines) + "\n"


def select(rows, wanted):
    """The rows of the wanted ids, and an error for each id that is no unit."""
    if not wanted:
        return rows, []
    known = {row["id"] for row in rows}
    errors = [
        f"{ident} is not a unit in scope" for ident in wanted if ident not in known
    ]
    return [row for row in rows if row["id"] in wanted], errors


def main(argv):
    rows, errors = select(numbers(repo_root(Path.cwd())), argv[1:])
    for error in errors:
        print(error, file=sys.stderr)
    sys.stdout.write(render(rows))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
