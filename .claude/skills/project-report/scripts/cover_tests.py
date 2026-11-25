#!/usr/bin/env python3
"""Run the unit tests and write the coverage map.

Line coverage names the test that executed each Python file. A data file
is not executed, so a read during a test is recorded for that test. A
Python import is not recorded that way: the first importer would own the
file. make test-changed reads the map. Hand-editing it is a defect.
"""

import importlib.util
import json
import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from types import FrameType


def module_name(path: str) -> str:
    text = path.replace("\\", "/")
    if text.endswith(".py"):
        text = text[: -len(".py")]
    return text.replace("/", ".")


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


def current_test(qualname_from_frame: Callable[[FrameType], str | None]) -> str:
    frame = sys._getframe(1)
    while frame is not None:
        name = frame.f_code.co_name
        if name.startswith("test") or name == "runTest":
            qualified = qualname_from_frame(frame)
            if qualified:
                return qualified
        frame = frame.f_back
    return ""


def relative_data_file(root: Path, file) -> str | None:
    if isinstance(file, bytes):
        try:
            file = file.decode()
        except UnicodeDecodeError:
            return None
    if isinstance(file, int) or not isinstance(file, (str, Path)):
        return None
    try:
        resolved = Path(file).resolve()
    except OSError:
        return None
    if not resolved.is_file():
        return None
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    if (
        relative.startswith("build/")
        or relative.endswith(".py")
        or relative.endswith(".pyc")
    ):
        return None
    return relative


def measured_files(root: Path, data) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for filename in data.measured_files():
        path = Path(filename)
        if path.is_absolute():
            try:
                relative = path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
        else:
            relative = path.as_posix()
        if not relative or relative.startswith("build/"):
            continue
        contexts = data.contexts_by_lineno(filename)
        tests = set()
        for names in contexts.values():
            for name in names:
                if name:
                    tests.add(name)
        for test_id in tests:
            found.setdefault(test_id, set()).add(relative)
    return found


def main(argv: list[str]) -> int:
    import coverage
    from coverage.context import qualname_from_frame

    root = sibling("requirements").repo_root(Path.cwd())
    sys.path.insert(0, str(root))
    if (root / "src").is_dir():
        sys.path.insert(0, str(root / "src"))
    reads: dict[str, set[str]] = {}

    def audit(event, args):
        if event != "open" or not args:
            return
        test_id = current_test(qualname_from_frame)
        if not test_id:
            return
        relative = relative_data_file(root, args[0])
        if relative is None:
            return
        reads.setdefault(test_id, set()).add(relative)

    destination = root / "build" / "coverage"
    destination.mkdir(parents=True, exist_ok=True)
    cov = coverage.Coverage(config_file=str(root / ".coveragerc"))
    sys.addaudithook(audit)
    cov.start()
    code = 1
    try:
        modules = [module_name(path) for path in argv[1:]]
        program = unittest.main(argv=["unittest", *modules], exit=False, module=None)
        code = 0 if program.result.wasSuccessful() else 1
    finally:
        cov.stop()
        cov.save()
        covered = sibling("select_tests").merge_covered(
            measured_files(root, cov.get_data()), reads
        )
        (destination / "covered.json").write_text(
            json.dumps(covered, indent=2) + "\n", encoding="utf-8"
        )
        cov.xml_report(outfile=str(destination / "coverage.xml"))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
