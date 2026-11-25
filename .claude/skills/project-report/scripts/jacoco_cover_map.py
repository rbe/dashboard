#!/usr/bin/env python3
"""Write the coverage map of a JVM project.

JaCoCo appends one session to the execution data file for each test
JVM. A test class covers each class that ran in the same JVM. Gradle
starts one JVM for each test class when the test task sets
forkEvery = 1. With one JVM for all tests, every test covers every
file, and make test-changed runs the full suite. The map is
build/coverage/covered.json, the file make test-changed reads.
"""

import importlib.util
import json
import struct
import sys
from pathlib import Path

SKIP = {".claude", ".git", ".gradle", "apm_modules", "build", "node_modules", "out"}
SOURCE = (".java", ".groovy", ".kt")
HEADER = 0x01
SESSION = 0x10
EXECUTION = 0x11


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


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.position = 0

    def done(self) -> bool:
        return self.position >= len(self.data)

    def take(self, count: int) -> bytes:
        chunk = self.data[self.position : self.position + count]
        if len(chunk) != count:
            raise ValueError("the execution data file ends inside a block")
        self.position += count
        return chunk

    def text(self) -> str:
        (length,) = struct.unpack(">H", self.take(2))
        return self.take(length).decode("utf-8", "replace")

    def number(self) -> int:
        value = 0
        shift = 0
        while True:
            byte = self.take(1)[0]
            value |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                return value
            shift += 7


def sessions(data: bytes) -> list[set[str]]:
    """The class names with a hit, for each session in the file."""
    found: list[set[str]] = []
    reader = Reader(data)
    while not reader.done():
        block = reader.take(1)[0]
        if block == HEADER:
            reader.take(4)
        elif block == SESSION:
            reader.text()
            reader.take(16)
            found.append(set())
        elif block == EXECUTION:
            reader.take(8)
            name = reader.text()
            probes = reader.take((reader.number() + 7) // 8)
            if not found:
                found.append(set())
            if any(probes):
                found[-1].add(name)
        else:
            raise ValueError(f"unknown block {block:#x} in the execution data file")
    return found


def sources(root: Path) -> dict[str, list[str]]:
    """Source files by the name a class file has: package path and outer class."""
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in SOURCE or not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP for part in relative.parts):
            continue
        parts = relative.with_suffix("").parts
        for start in range(len(parts)):
            found.setdefault("/".join(parts[start:]), []).append(relative.as_posix())
    return found


def is_test(relative: str) -> bool:
    parts = relative.split("/")
    return any(part in ("test", "integrationTest") for part in parts[:-1])


def covered(files: list[Path], root: Path) -> dict[str, set[str]]:
    index = sources(root)
    found: dict[str, set[str]] = {}
    for file in files:
        for names in sessions(file.read_bytes()):
            paths = set()
            tests = set()
            for name in names:
                outer = name.split("$", 1)[0]
                for path in index.get(outer, []):
                    paths.add(path)
                    if is_test(path):
                        tests.add(outer.replace("/", "."))
            for test in tests:
                found.setdefault(test, set()).update(paths)
    return found


def main(argv: list[str]) -> int:
    root = Path.cwd()
    files = [Path(name) for name in argv[1:]]
    if not files:
        files = sorted(root.glob("build/jacoco/*.exec"))
        files += sorted(root.glob("*/build/jacoco/*.exec"))
    if not files:
        print("coverage map: no JaCoCo execution data file", file=sys.stderr)
        return 1
    found = sibling("select_tests").merge_covered(covered(files, root), {})
    if not found:
        print("coverage map: no test class ran under JaCoCo", file=sys.stderr)
        return 1
    destination = root / "build" / "coverage"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "covered.json").write_text(
        json.dumps(found, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
