#!/usr/bin/env python3
"""Run pytest for make coverage and make test-changed.

cover_tests.py and changed_tests.py run unittest. A project whose tests
are pytest functions with fixtures runs this script instead. It writes
the same coverage map and selects tests from it the same way:

    pytest_cover.py cover [PYTEST_ARGS...]    write build/coverage/coverage.xml and covered.json
    pytest_cover.py changed [PYTEST_ARGS...]  run the tests that cover the files of the diff

The project needs pytest and coverage.py where the script runs.
"""

import json
import sys
from pathlib import Path

PYTEST_ARGS = ["-q", "-p", "no:cacheprovider"]


def cover_tests():
    import importlib.util

    loaded = sys.modules.get("_project_report_cover_tests")
    if loaded is not None:
        return loaded
    path = Path(__file__).resolve().parent / "cover_tests.py"
    spec = importlib.util.spec_from_file_location("_project_report_cover_tests", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    if spec.loader is None:
        raise ImportError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def node_id(root: Path, test_id: str) -> str | None:
    """The test id tests.test_x.TestY.test_z as the pytest node tests/test_x.py::TestY::test_z."""
    parts = test_id.split(".")
    for cut in range(len(parts), 0, -1):
        path = root.joinpath(*parts[:cut]).with_suffix(".py")
        if path.is_file():
            rest = parts[cut:]
            relative = path.relative_to(root).as_posix()
            return "::".join([relative, *rest]) if rest else relative
    return None


def cover(root: Path, extra: list[str]) -> int:
    """Run the whole suite under coverage.py and write the coverage map."""
    import coverage
    import pytest
    from coverage.context import qualname_from_frame

    helpers = cover_tests()
    sys.path.insert(0, str(root))
    if (root / "src").is_dir():
        sys.path.insert(0, str(root / "src"))
    reads: dict[str, set[str]] = {}

    def audit(event, args):
        if event != "open" or not args:
            return
        test_id = helpers.current_test(qualname_from_frame)
        if not test_id:
            return
        relative = helpers.relative_data_file(root, args[0])
        if relative is not None:
            reads.setdefault(test_id, set()).add(relative)

    destination = root / "build" / "coverage"
    destination.mkdir(parents=True, exist_ok=True)
    cov = coverage.Coverage(config_file=str(root / ".coveragerc"))
    sys.addaudithook(audit)
    cov.start()
    code = 1
    try:
        code = int(pytest.main([*PYTEST_ARGS, *extra]))
    finally:
        cov.stop()
        cov.save()
        covered = helpers.sibling("select_tests").merge_covered(
            helpers.measured_files(root, cov.get_data()), reads
        )
        (destination / "covered.json").write_text(
            json.dumps(covered, indent=2) + "\n", encoding="utf-8"
        )
        cov.xml_report(outfile=str(destination / "coverage.xml"))
    return code


def chosen_nodes(root: Path) -> list[str] | None:
    """The pytest nodes that cover the files of the diff, or None when an input is missing."""
    coverage_dir = root / "build" / "coverage"
    covered_path = coverage_dir / "covered.json"
    changed_path = coverage_dir / "changed.txt"
    if not covered_path.is_file():
        print(
            "test-changed: the coverage map is missing. Run make coverage. make test runs the full suite.",
            file=sys.stderr,
        )
        return None
    if not changed_path.is_file():
        print(
            "test-changed: the diff list is missing. Run make test-changed.",
            file=sys.stderr,
        )
        return None
    files = [
        line.strip()
        for line in changed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    covered = json.loads(covered_path.read_text(encoding="utf-8"))
    chosen = cover_tests().sibling("select_tests").select(files, covered)
    return sorted({node for node in (node_id(root, test) for test in chosen) if node})


def changed(root: Path, extra: list[str]) -> int:
    """Run the tests that the coverage map names for the files of the diff."""
    nodes = chosen_nodes(root)
    if nodes is None:
        return 1
    if not nodes:
        print(
            "test-changed: no test covers the changed files. make test runs the full suite."
        )
        return 0
    import pytest

    print(f"test-changed: {len(nodes)} tests", flush=True)
    return int(pytest.main([*PYTEST_ARGS, *extra, *nodes]))


def main(argv: list[str]) -> int:
    root = cover_tests().sibling("requirements").repo_root(Path.cwd())
    if argv[1:2] == ["cover"]:
        return cover(root, argv[2:])
    if argv[1:2] == ["changed"]:
        return changed(root, argv[2:])
    print("usage: pytest_cover.py cover|changed [PYTEST_ARGS...]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
