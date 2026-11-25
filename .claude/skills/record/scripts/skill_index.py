#!/usr/bin/env python3
"""Write docs/skill-index.toon from installed skill frontmatter."""

import sys
from pathlib import Path

COLUMNS = ("name", "kind", "order", "files", "names")


def repo_root(start):
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir() or (candidate / "skills").is_dir():
            return candidate
    return current


def skill_root(root):
    installed = root / ".claude" / "skills"
    if installed.is_dir() and any(installed.glob("*/SKILL.md")):
        return installed
    bundled = root / "skills"
    if bundled.is_dir() and any(bundled.glob("*/SKILL.md")):
        return bundled
    return installed


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
        if value in ("", "[]"):
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


def rows(root):
    found = []
    directory = skill_root(root)
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*/SKILL.md")):
        data = frontmatter(path.read_text(encoding="utf-8"))
        kind = data.get("kind", "")
        if kind not in ("language", "check"):
            continue
        order = data.get("order", "")
        if isinstance(order, list):
            order = ""
        found.append(
            {
                "name": data.get("name", path.parent.name),
                "kind": kind,
                "order": str(order),
                "files": data.get("files", [])
                if isinstance(data.get("files", []), list)
                else [],
                "names": data.get("names", [])
                if isinstance(data.get("names", []), list)
                else [],
            }
        )

    def sort_key(row):
        try:
            order = int(row["order"]) if row["order"] != "" else 0
        except ValueError:
            order = 0
        return (0 if row["kind"] == "check" else 1, order, row["name"])

    return sorted(found, key=sort_key)


def name_errors(root):
    errors = []
    directory = skill_root(root)
    if not directory.is_dir():
        return errors
    for path in sorted(directory.glob("*/SKILL.md")):
        data = frontmatter(path.read_text(encoding="utf-8"))
        name = data.get("name", "")
        if name != path.parent.name:
            errors.append(
                f"{path.parent.name}: the frontmatter name is {name or 'missing'}"
            )
    return errors


def yaml_errors(root):
    """A plain frontmatter value that YAML would not read as one string."""
    errors = []
    directory = skill_root(root)
    if not directory.is_dir():
        return errors
    for path in sorted(directory.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        end = text.find("\n---", 3)
        if not text.startswith("---") or end < 0:
            errors.append(f"{path.parent.name}: the frontmatter is missing")
            continue
        for line in text[3:end].splitlines():
            if ":" not in line or line.startswith((" ", "\t", "#", "-")):
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if not value or value[0] in "'\"[{|>":
                continue
            if ": " in value or " #" in value or value.endswith(":"):
                errors.append(
                    f"{path.parent.name}: the value of {key.strip()} is not one "
                    "YAML string. Remove the colon or the # from it"
                )
    return errors


def render(found):
    lines = [f"skill_index[{len(found)}]{{{','.join(COLUMNS)}}}:"]
    for row in found:
        lines.append("  " + ",".join(cell(row[key]) for key in COLUMNS))
    return "\n".join(lines) + "\n"


def write(root):
    text = render(rows(root))
    destination = root / "docs" / "skill-index.toon"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def main():
    root = repo_root(Path.cwd())
    write(root)
    errors = name_errors(root) + yaml_errors(root)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
