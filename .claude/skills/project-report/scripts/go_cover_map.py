#!/usr/bin/env python3
"""Write the coverage map and the Cobertura file of a Go project.

make coverage runs the tests of each package with a cover profile in
build/coverage/go/. A package covers each Go file its tests ran. The map
is build/coverage/covered.json, the file make test-changed reads. The
Cobertura file is build/coverage/coverage.xml, the file diff-cover reads.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

BLOCK = re.compile(
    r"^(?P<file>.+):(?P<start>\d+)\.\d+,(?P<end>\d+)\.\d+ \d+ (?P<count>\d+)$"
)


def sibling(name: str):
    loaded = sys.modules.get(f"_project_report_{name}")
    if loaded is not None:
        return loaded
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_project_report_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    if spec.loader is None:
        raise ImportError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def module_path(root: Path) -> str:
    for line in (root / "go.mod").read_text(encoding="utf-8").splitlines():
        if line.startswith("module "):
            return line.split(None, 1)[1].strip()
    raise ValueError("go.mod has no module line")


def blocks(profile: Path, module: str) -> list[tuple[str, int, int, int]]:
    """Each block of a profile: the file in the project, the lines, the count."""
    found = []
    for line in profile.read_text(encoding="utf-8").splitlines():
        match = BLOCK.match(line.strip())
        if match is None:
            continue
        name = match.group("file")
        if name == module or not name.startswith(module + "/"):
            continue
        relative = name[len(module) + 1 :]
        found.append(
            (
                relative,
                int(match.group("start")),
                int(match.group("end")),
                int(match.group("count")),
            )
        )
    return found


def packages(root: Path) -> dict[str, str]:
    """Each directory with a Go test file, by the flat name of its profile."""
    module = module_path(root).replace("/", "_")
    found = {}
    for path in sorted(root.rglob("*_test.go")):
        relative = path.parent.relative_to(root).as_posix()
        if relative == ".":
            found[module] = "."
        else:
            found[module + "_" + relative.replace("/", "_")] = "./" + relative
    return found


def covered(
    directory: Path, root: Path
) -> tuple[dict[str, set[str]], dict[str, dict[int, int]]]:
    module = module_path(root)
    tests = packages(root)
    by_test: dict[str, set[str]] = {}
    lines: dict[str, dict[int, int]] = {}
    for profile in sorted(directory.glob("*.out")):
        package = tests.get(profile.stem)
        for relative, start, end, count in blocks(profile, module):
            hits = lines.setdefault(relative, {})
            for number in range(start, end + 1):
                hits[number] = max(hits.get(number, 0), count)
            if package is not None and count > 0:
                by_test.setdefault(package, set()).add(relative)
    # A package with tests covers its own test files, also when its tests
    # ran no statement of the project. A change to a test file selects it.
    for package in tests.values():
        for path in sorted((root / package).glob("*_test.go")):
            by_test.setdefault(package, set()).add(path.relative_to(root).as_posix())
    return by_test, lines


def cobertura(lines: dict[str, dict[int, int]]) -> str:
    out = [
        '<?xml version="1.0" ?>',
        '<coverage version="1">',
        "  <sources><source>.</source></sources>",
        "  <packages>",
        '    <package name="go">',
        "      <classes>",
    ]
    for name in sorted(lines):
        out.append(f"        <class name={quoteattr(name)} filename={quoteattr(name)}>")
        out.append("          <lines>")
        for number in sorted(lines[name]):
            out.append(
                f'            <line number="{number}" hits="{lines[name][number]}"/>'
            )
        out.append("          </lines>")
        out.append("        </class>")
    out += ["      </classes>", "    </package>", "  </packages>", "</coverage>"]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    root = Path.cwd()
    directory = Path(argv[1]) if len(argv) > 1 else root / "build/coverage/go"
    if not directory.is_dir() or not any(directory.glob("*.out")):
        print(
            "coverage map: no Go cover profile. No test file exists yet.",
            file=sys.stderr,
        )
        return 1
    by_test, lines = covered(directory, root)
    found = sibling("select_tests").merge_covered(by_test, {})
    if not found:
        print("coverage map: no Go test ran a file of the project", file=sys.stderr)
        return 1
    destination = root / "build" / "coverage"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "covered.json").write_text(
        json.dumps(found, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "coverage.xml").write_text(cobertura(lines), encoding="utf-8")
    # The next run starts with no profile from this run.
    for profile in directory.glob("*.out"):
        profile.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
