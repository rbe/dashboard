#!/usr/bin/env python3
"""Rewrite a JaCoCo XML report so that diff-cover finds the sources of every module.

JaCoCo names a source file by package and file name, for example
org/odisee/document/OfficeDocument.java. diff-cover joins the source root
src/main/java with that name, which fits one module with one source tree. A
build with several modules or Groovy trees needs more. The script finds each source file in
the repository and gives its package a name that starts with ../../../ and the
directory of the source root, so that the join ends at the path from the
repository root.

Usage: jacoco_repo_paths.py REPORT.xml OUTPUT.xml
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SKIP = {".claude", ".git", ".gradle", "apm_modules", "build", "node_modules"}
SOURCE = (".java", ".groovy", ".kt")
ROOT_DEPTH = "../../../"  # src/main/java is three directories below the repository root


def source_files(root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in SOURCE or not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP for part in relative.parts):
            continue
        found.setdefault(path.name, []).append(relative.as_posix())
    return found


def repository_path(index: dict[str, list[str]], package: str, name: str) -> str | None:
    suffix = f"{package}/{name}" if package else name
    candidates = [
        p for p in index.get(name, []) if p == suffix or p.endswith("/" + suffix)
    ]
    main = [p for p in candidates if "/test/" not in p and "/integrationTest/" not in p]
    chosen = main or candidates
    return chosen[0] if chosen else None


def main(argv: list[str]) -> int:
    report, output = Path(argv[1]), Path(argv[2])
    tree = ET.parse(report)
    root = tree.getroot()
    index = source_files(Path.cwd())
    for package in list(root.findall("package")):
        position = list(root).index(package)
        root.remove(package)
        for sourcefile in package.findall("sourcefile"):
            name = package.get("name", "")
            path = repository_path(index, name, sourcefile.get("name", ""))
            if path is None:
                continue
            tail = (
                f"{name}/{sourcefile.get('name')}" if name else sourcefile.get("name")
            )
            directory = path[: -len(tail)].rstrip("/")
            moved = ET.Element(
                "package",
                {"name": ROOT_DEPTH + (directory + "/" if directory else "") + name},
            )
            moved.append(sourcefile)
            root.insert(position, moved)
            position += 1
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
