#!/usr/bin/env python3
"""Run the tests that cover the files in the diff.

The coverage map is build/coverage/covered.json, written by make coverage.
The diff list is build/coverage/changed.txt, written by make test-changed.
A green run does not replace make test.

With --print, the chosen tests are printed, one on each line, and no
test runs. A Node or JVM project gives that list to its own runner.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


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


def run(root: Path, only_print: bool = False) -> int:
    coverage = root / "build" / "coverage"
    covered_path = coverage / "covered.json"
    changed_path = coverage / "changed.txt"
    if not covered_path.is_file():
        print(
            "test-changed: coverage map is missing. Run make coverage. "
            "make test runs the full suite.",
            file=sys.stderr,
        )
        return 1
    if not changed_path.is_file():
        print(
            "test-changed: diff list is missing. Run make test-changed.",
            file=sys.stderr,
        )
        return 1
    changed = [
        line.strip()
        for line in changed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    covered = json.loads(covered_path.read_text(encoding="utf-8"))
    chosen = sibling("select_tests").select(changed, covered)
    if only_print:
        for test_id in chosen:
            print(test_id)
        return 0
    if not chosen:
        print(
            "test-changed: no test covers the changed files. make test runs the full suite."
        )
        return 0
    print("test-changed: " + " ".join(chosen), flush=True)
    result = subprocess.run([sys.executable, "-m", "unittest", *chosen], check=False)
    return result.returncode


def main(argv: list[str]) -> int:
    if "--print" in argv[1:]:
        return run(Path.cwd(), only_print=True)
    root = sibling("requirements").repo_root(Path.cwd())
    return run(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
