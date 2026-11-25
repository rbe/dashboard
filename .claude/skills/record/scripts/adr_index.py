#!/usr/bin/env python3
"""Write docs/adr/index.toon from ADR frontmatter. Skills are not indexed."""

import sys
from pathlib import Path

COLUMNS = ("id", "status", "title", "adrs", "skills", "roadmap")


def repo_root(start):
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir():
            return candidate
    return current


def frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    data = {}
    current = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith(" ") and current:
            item = line.strip().lstrip("-").strip().strip("'\"")
            if item:
                data.setdefault(current, [])
                if isinstance(data[current], list):
                    data[current].append(item)
            continue
        if ":" not in line:
            current = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current = key
        if value == "" or value == "[]":
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            data[key] = value.strip("'\"")
    return data


def cell(value):
    if isinstance(value, list):
        text = ";".join(value)
    else:
        text = "" if value is None else str(value)
    if any(character in text for character in ',"\n'):
        return '"' + text.replace('"', '""') + '"'
    return text


def rows(adr_dir):
    found = []
    if not adr_dir.is_dir():
        return found
    for path in sorted(adr_dir.glob("*.md")):
        data = frontmatter(path.read_text(encoding="utf-8"))
        if "id" not in data:
            continue
        found.append(
            {
                key: data.get(key, [] if key in {"adrs", "skills", "roadmap"} else "")
                for key in COLUMNS
            }
        )
    return found


def render(found):
    lines = [f"adr_index[{len(found)}]{{{','.join(COLUMNS)}}}:"]
    for row in found:
        lines.append("  " + ",".join(cell(row[key]) for key in COLUMNS))
    return "\n".join(lines) + "\n"


def main():
    root = repo_root(Path.cwd())
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    text = render(rows(adr_dir))
    (adr_dir / "index.toon").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
