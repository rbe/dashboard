#!/usr/bin/env python3
"""Write docs/requirements-index.toon from the requirement files.

The rows stand in docs/requirements/<owner>.md, one file for each skill
that owns them. The index lists the id, the title, the status, the file,
and the owner of each row.
"""

import re
import sys
from pathlib import Path

COLUMNS = ("id", "title", "status", "file", "owner")
ID_CELL = re.compile(r"^[A-Z]+-\d+$")
IN_FORCE = "in force"


def repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir():
            return candidate
    return current


def strip_anchor(cell: str) -> str:
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import links

    return links.strip_anchor(cell)


def requirement_files(root: Path) -> list[Path]:
    """The files of docs/requirements/, in name order."""
    folder = root / "docs" / "requirements"
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def file_rows(path: Path) -> list[dict[str, str]]:
    """Each row of one file as id, title, status, and statement.

    A table with a column Status gives the status. A row of a table with no
    such column is in force. A table with no column Statement gives an empty
    statement.
    """
    found: list[dict[str, str]] = []
    if not path.is_file():
        return found
    status_at = None
    statement_at = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [part.strip() for part in stripped.strip("|").split("|")]
        ident = strip_anchor(cells[0]) if cells else ""
        if ident == "Id":
            lowered = [cell.lower() for cell in cells]
            status_at = lowered.index("status") if "status" in lowered else None
            statement_at = (
                lowered.index("statement") if "statement" in lowered else None
            )
            continue
        if len(cells) < 2 or ID_CELL.match(ident) is None:
            continue
        status = cells[status_at] if status_at and status_at < len(cells) else ""
        statement = (
            cells[statement_at] if statement_at and statement_at < len(cells) else ""
        )
        found.append(
            {
                "id": ident,
                "title": cells[1],
                "status": status or IN_FORCE,
                "statement": statement,
            }
        )
    return found


def rows(root: Path) -> list[dict[str, str]]:
    """Each row of every requirement file, with its file and its owner."""
    found = []
    for path in requirement_files(root):
        relative = path.relative_to(root).as_posix()
        for row in file_rows(path):
            found.append({**row, "file": relative, "owner": path.stem})
    return found


def cell(value: str) -> str:
    if any(character in value for character in ',"\n'):
        return '"' + value.replace('"', '""') + '"'
    return value


def render(found: list[dict[str, str]]) -> str:
    lines = [f"requirements[{len(found)}]{{{','.join(COLUMNS)}}}:"]
    for row in found:
        lines.append("  " + ",".join(cell(row[column]) for column in COLUMNS))
    return "\n".join(lines) + "\n"


def write(root: Path) -> Path:
    text = render(rows(root))
    destination = root / "docs" / "requirements-index.toon"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def main() -> int:
    write(repo_root(Path.cwd()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
