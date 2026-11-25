#!/usr/bin/env python3
"""Write the document index and the installed-skill index.

A product repository gets the ADR index. A repository that keeps
docs/requirements/ and no ADR file gets the requirements index
instead. When both are present, the ADR index is the one that is written.
"""

import os
import sys
from pathlib import Path


def load():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import adr_index
    import requirements_index
    import skill_index

    return adr_index, requirements_index, skill_index


def has_adr_markdown(root: Path) -> bool:
    adr_dir = root / "docs" / "adr"
    return adr_dir.is_dir() and any(adr_dir.glob("*.md"))


def uses_requirements_list(root: Path) -> bool:
    _adr_index, requirements_index, _skill_index = load()
    return bool(requirements_index.requirement_files(root)) and not has_adr_markdown(
        root
    )


def write_indexes(root: Path) -> None:
    adr_index, requirements_index, skill_index = load()
    if uses_requirements_list(root):
        requirements_index.write(root)
    else:
        previous = Path.cwd()
        try:
            os.chdir(root)
            adr_index.main()
        finally:
            os.chdir(previous)
    skill_index.write(root)


def main():
    _adr_index, _requirements_index, skill_index = load()
    root = skill_index.repo_root(Path.cwd())
    write_indexes(root)
    errors = skill_index.name_errors(root) + skill_index.yaml_errors(root)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
