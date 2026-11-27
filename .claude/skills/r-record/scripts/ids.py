#!/usr/bin/env python3
"""Check the ids of the board, and issue the next id of a kind.

docs/ids.yaml holds one counter for each kind of id, one line `R: 83`. A
counter is the highest number issued. It only grows, so a deleted id is
never issued again. An id is valid when its number is not above the counter
of its kind. A history id has no counter.
"""

import re
import sys
from pathlib import Path

ID_LINE = re.compile(r"^id:\s*[\"']?([^\"'#\s]+)")
ROW_ID = re.compile(r'^\|\s*(?:<a id="[^"]*"></a>)?\s*([A-Z]+-\d+)\s*\|')
COUNTER_LINE = re.compile(r"^([A-Z]+):\s*(\d+)$")
NUMBERED = re.compile(r"(ADR|[A-Z])-(\d+)")
# The kinds that `make id` issues. A counter of another kind in the file is
# a kind too, as `D` in a repository that kept the old decisions.
KINDS = ("R", "W", "ADR", "P")
ID_FORM = re.compile(
    r"ADR-\d{4}|H-\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]-\d+"
)
# `decisions` and `issues` are the keys of a history file written before
# the roadmap table. A new file writes `roadmap`. The check is the same.
LIST_KEY = re.compile(r"^(adrs|decisions|issues|roadmap|proposals|supersedes):(.*)$")
FRONT_KEY = re.compile(r"^([A-Za-z_]+):(.*)$")
ADR_STATUSES = ("Accepted", "Superseded")
ADR_FORBIDDEN_KEYS = ("version", "date")


def repo_root(start):
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir():
            return candidate
    return current


def table_paths(docs):
    """The roadmap and each file of docs/requirements/."""
    return [*sorted((docs / "requirements").glob("*.md")), docs / "ROADMAP.md"]


def table_ids(docs):
    found = {}
    if not docs.is_dir():
        return found
    for path in table_paths(docs):
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = ROW_ID.match(line.strip())
            if match:
                found.setdefault(match.group(1), []).append(f"{path}:{number}")
    return found


def live_ids(docs):
    found = table_ids(docs)
    if not docs.is_dir():
        return found
    for path in sorted(docs.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        if path.name == "ids.yaml":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = ID_LINE.match(line.strip())
            if match:
                found.setdefault(match.group(1), []).append(f"{path}:{number}")
    return found


def split_id(ident):
    """The kind and the number of an id that has a counter, else None."""
    match = NUMBERED.fullmatch(ident)
    if match is None or match.group(1) == "H":
        return None
    return match.group(1), int(match.group(2))


def format_id(kind, number):
    return f"ADR-{number:04d}" if kind == "ADR" else f"{kind}-{number}"


def read_counters(path):
    """The counters of ids.yaml as a dict in file order, and the errors."""
    counters = {}
    errors = []
    if not path.is_file():
        return counters, errors
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = COUNTER_LINE.match(stripped)
        if match is None:
            errors.append(f"{path}:{number} is not a counter such as R: 83")
        elif match.group(1) in counters:
            errors.append(f"{path}:{number} has a second counter for {match.group(1)}")
        else:
            counters[match.group(1)] = int(match.group(2))
    return counters, errors


def write_counters(path, counters):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{kind}: {number}" for kind, number in counters.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def highest_live(live, kind):
    numbers = [0]
    for ident in live:
        parts = split_id(ident)
        if parts and parts[0] == kind:
            numbers.append(parts[1])
    return max(numbers)


def front_lists(lines):
    """Each list key of the frontmatter as (line index, key, text after the colon)."""
    if not lines or lines[0].strip() != "---":
        return []
    found = []
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            break
        match = LIST_KEY.match(lines[index])
        if match:
            found.append((index, match.group(1), match.group(2).strip()))
    return found


def list_items(text):
    """The items of a list written on one line, or None when it is not one."""
    if not (text.startswith("[") and text.endswith("]")):
        return None
    return [item.strip().strip("'\"") for item in text[1:-1].split(",") if item.strip()]


def above_counter(ident, counters):
    """The error text when an id has no counter or is above it, else None."""
    parts = split_id(ident)
    if parts is None:
        return None
    kind, number = parts
    if kind not in counters:
        return f"{ident} has no counter: docs/ids.yaml has no line for {kind}"
    if number > counters[kind]:
        return f"{ident} is above the counter {kind}: {counters[kind]} of docs/ids.yaml"
    return None


def list_errors(docs, counters):
    """A frontmatter list is [a, b], and [] when empty. Each item is an id that is not above its counter."""
    errors = []
    for path in sorted(docs.rglob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, key, text in front_lists(lines):
            place = f"{path}:{index + 1}"
            items = list_items(text)
            if items is None:
                errors.append(f"{place} {key} is not a list on one line: write []")
                continue
            for item in items:
                if not ID_FORM.fullmatch(item):
                    errors.append(f"{place} {key} holds {item}, which is not an id")
                    continue
                problem = above_counter(item, counters)
                if problem:
                    errors.append(f"{place} {key} names {item}: {problem}")
    return errors


def front_keys(lines):
    """The key and value of each frontmatter line that starts at the margin."""
    if not lines or lines[0].strip() != "---":
        return []
    found = []
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            break
        match = FRONT_KEY.match(lines[index])
        if match:
            found.append((index, match.group(1), match.group(2).strip().strip("'\"")))
    return found


def adr_errors(docs):
    """An ADR has no `version` key and no `date` key, and its status is Accepted or Superseded."""
    errors = []
    for path in sorted((docs / "adr").glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, key, value in front_keys(lines):
            place = f"{path}:{index + 1}"
            if key in ADR_FORBIDDEN_KEYS:
                errors.append(f"{place} an ADR has no {key} key: Git holds it")
            elif key == "status" and value not in ADR_STATUSES:
                errors.append(
                    f"{place} status is {value}: write Accepted or Superseded"
                )
    return errors


def check(root):
    docs = root / "docs"
    live = live_ids(docs)
    counters, errors = read_counters(docs / "ids.yaml")
    if (docs / "REQUIREMENTS.md").exists():
        errors.append(
            f"{docs / 'REQUIREMENTS.md'} exists: move its rows to docs/requirements/<skill>.md"
        )
    errors += list_errors(docs, counters)
    errors += adr_errors(docs)
    for ident, places in sorted(live.items()):
        if len(places) > 1:
            errors.append(f"{ident} is used {len(places)} times: {', '.join(places)}")
        problem = above_counter(ident, counters)
        if problem:
            errors.append(f"{places[0]} {problem}")
    return errors


def next_id(root, kind):
    """Issue the next id of a kind: raise its counter by one and return the id."""
    path = root / "docs" / "ids.yaml"
    counters, errors = read_counters(path)
    if errors:
        return None, errors
    if kind not in KINDS and kind not in counters:
        return None, [f"{kind} is not a kind with a counter: {', '.join(KINDS)}"]
    live = live_ids(root / "docs")
    for known in KINDS:
        counters[known] = max(counters.get(known, 0), highest_live(live, known))
    counters[kind] = max(counters[kind], highest_live(live, kind)) + 1
    write_counters(path, counters)
    return format_id(kind, counters[kind]), []


def raise_counter(root, kind, number):
    """Set the counter of a kind to number. A counter never goes down."""
    if not re.fullmatch(r"[A-Z]+", kind):
        return [f"{kind} is not a kind: write capital letters"]
    path = root / "docs" / "ids.yaml"
    counters, errors = read_counters(path)
    if errors:
        return errors
    if number <= counters.get(kind, -1):
        return [f"The counter {kind} is {counters[kind]}, not below {number}"]
    counters[kind] = number
    write_counters(path, counters)
    return []


def usage():
    print("usage: ids.py | ids.py id KIND | ids.py raise KIND NUMBER", file=sys.stderr)
    return 2


def main(argv):
    root = repo_root(Path.cwd())
    if len(argv) == 3 and argv[1] == "id":
        ident, errors = next_id(root, argv[2])
        if ident:
            print(ident)
    elif len(argv) == 4 and argv[1] == "raise" and argv[3].isdigit():
        errors = raise_counter(root, argv[2], int(argv[3]))
    elif len(argv) == 1:
        errors = check(root)
    else:
        return usage()
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
