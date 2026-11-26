#!/usr/bin/env python3
"""Choose tests from coverage of the files in the diff."""

from collections.abc import Iterable, Mapping


def normalize(path: str) -> str:
    text = str(path).replace("\\", "/").strip()
    if text.startswith("./"):
        text = text[2:]
    return text


def merge_covered(
    measured: Mapping[str, Iterable[str]],
    reads: Mapping[str, Iterable[str]],
) -> dict[str, list[str]]:
    """Union line coverage and files a test read. An empty test id is dropped."""
    found: dict[str, set[str]] = {}
    for source in (measured, reads):
        for test_id, files in source.items():
            if not test_id:
                continue
            bucket = found.setdefault(test_id, set())
            for file in files:
                path = normalize(file)
                if not path or path.startswith("build/"):
                    continue
                bucket.add(path)
    return {test_id: sorted(files) for test_id, files in sorted(found.items())}


def select(changed: Iterable[str], covered: Mapping[str, Iterable[str]]) -> list[str]:
    """Tests whose coverage includes a changed file. The map is the only input."""
    wanted = {normalize(path) for path in changed if normalize(path)}
    chosen = []
    for test_id in sorted(covered):
        if not test_id:
            continue
        files = {normalize(path) for path in covered[test_id]}
        if files & wanted:
            chosen.append(test_id)
    return chosen
