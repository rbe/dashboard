#!/usr/bin/env python3
"""Write the coverage map of a Node project.

Node writes one V8 coverage file for each process when NODE_V8_COVERAGE
names a directory. A test file covers each project file that ran in the
same process. The map is build/coverage/covered.json, the file
make test-changed reads.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

SKIP = {".claude", ".git", "apm_modules", "build", "dist", "node_modules"}
TEST_NAME = re.compile(r"\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$")
TEST_DIRECTORY = {"test", "tests", "__tests__"}


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


def is_test(relative: str) -> bool:
    parts = relative.split("/")
    if TEST_NAME.search(parts[-1]):
        return True
    return any(part in TEST_DIRECTORY for part in parts[:-1])


def project_file(url: str, root: Path) -> str | None:
    """The path of a script inside the project, or None for any other script."""
    if not url.startswith("file://"):
        return None
    path = Path(unquote(urlparse(url).path))
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if any(part in SKIP for part in relative.parts):
        return None
    return relative.as_posix()


def ran(script: dict) -> bool:
    for function in script.get("functions", []):
        for block in function.get("ranges", []):
            if block.get("count", 0) > 0:
                return True
    return False


def covered(directory: Path, root: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        files = set()
        for script in data.get("result", []):
            relative = project_file(script.get("url", ""), root)
            if relative is not None and ran(script):
                files.add(relative)
        for test in sorted(file for file in files if is_test(file)):
            found.setdefault(test, set()).update(files)
    return found


def main(argv: list[str]) -> int:
    root = Path.cwd()
    directory = Path(argv[1]) if len(argv) > 1 else root / "build/coverage/v8"
    if not directory.is_dir():
        print(f"coverage map: {directory} is missing", file=sys.stderr)
        return 1
    found = sibling("select_tests").merge_covered(covered(directory, root), {})
    if not found:
        print(
            "coverage map: no test file ran under V8 coverage. "
            "No test file exists yet, or the runner is Vitest, whose workers "
            "write none. The r-node skill names the command for Vitest.",
            file=sys.stderr,
        )
        return 1
    destination = root / "build" / "coverage"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "covered.json").write_text(
        json.dumps(found, indent=2) + "\n", encoding="utf-8"
    )
    # The next run starts with no file from this run.
    for path in directory.glob("*.json"):
        path.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
