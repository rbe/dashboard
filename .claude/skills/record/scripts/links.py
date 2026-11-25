#!/usr/bin/env python3
"""Make every document id in running text a link.

An id is defined by a table row in a file of docs/requirements/,
in docs/ROADMAP.md, or by `id:` in the
frontmatter of a Markdown file. A table row gets an anchor. Every other
mention of the id in running text links to the definition.
"""

import posixpath
import re
import sys
from pathlib import Path

ID = r"(?:ADR-\d{4}|H-\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]-\d+)"
TOKEN = re.compile(rf"(?<![A-Za-z0-9-]){ID}(?![A-Za-z0-9-])")
WHOLE = re.compile(ID)
LINKED_ID = re.compile(rf"\[({ID})\]\([^)\s]*\)")
ANCHOR = re.compile(r'^<a id="[^"]*"></a>')
ROW = re.compile(rf'^(\s*\|)\s*(?:<a id="[^"]*"></a>)?\s*({ID})\s*\|')
ID_LINE = re.compile(r"^id:\s*[\"']?([^\"'#\s]+)")
SPANS = re.compile(
    r"(`+)(?:.+?)(?<!`)\1(?!`)"
    r"|!?\[[^\]]*\]\([^)]*\)"
    r"|\[[^\]]*\]\[[^\]]*\]"
    r"|<[A-Za-z/][^>\n]*>"
)


def table_paths(root: Path) -> list[Path]:
    """The files whose table rows define an id: the roadmap and each requirement file."""
    docs = root / "docs"
    listed = sorted((docs / "requirements").glob("*.md"))
    return [*listed, docs / "ROADMAP.md"]


def repo_root(start: Path) -> Path:
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docs").is_dir():
            return candidate
    return current


def strip_anchor(cell: str) -> str:
    """Remove a leading anchor from a table cell."""
    return ANCHOR.sub("", cell.strip()).strip()


def skipped(lines: list[str], front: bool = True) -> list[bool]:
    """Mark the lines inside a fenced block and, when asked, the frontmatter."""
    flags = [False] * len(lines)
    start = 0
    if front and lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                for inner in range(index + 1):
                    flags[inner] = True
                start = index + 1
                break
    fence = None
    for index in range(start, len(lines)):
        marker = lines[index].lstrip()[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            flags[index] = True
            continue
        flags[index] = fence is not None
    return flags


def comment_spans(line: str, inside: bool) -> tuple[list[tuple[int, int]], bool]:
    """The HTML comment spans of a line, and whether a comment stays open."""
    spans = []
    position = 0
    while True:
        if inside:
            end = line.find("-->", position)
            if end < 0:
                spans.append((position, len(line)))
                return spans, True
            spans.append((position, end + 3))
            position = end + 3
            inside = False
            continue
        start = line.find("<!--", position)
        if start < 0:
            return spans, False
        end = line.find("-->", start + 4)
        if end < 0:
            spans.append((start, len(line)))
            return spans, True
        spans.append((start, end + 3))
        position = end + 3


def first_cell(line: str) -> tuple[int, str]:
    """The end of the first cell of a table row, and the id in it."""
    if not line.lstrip().startswith("|"):
        return 0, ""
    first = line.find("|")
    end = line.find("|", first + 1)
    if end < 0:
        return 0, ""
    cell = strip_anchor(line[first + 1 : end])
    return end, cell if WHOLE.fullmatch(cell) else ""


def target_url(found: dict, ident: str, from_dir: str, own_path: str) -> str | None:
    path, anchor = found[ident]
    if path == own_path:
        return f"#{anchor}" if anchor else None
    url = posixpath.relpath(path, from_dir or ".")
    return f"{url}#{anchor}" if anchor else url


def link_line(
    line: str, found: dict, from_dir: str, own_path: str, spans: list, found_ids: list
) -> str:
    end, own_id = first_cell(line)
    if end:
        spans = [*spans, (0, end)]

    def replace(match: re.Match) -> str:
        ident = match.group()
        start = match.start()
        if own_id == ident or ident not in found:
            return ident
        if any(a <= start < b for a, b in spans):
            return ident
        if line[:start].endswith("/") or line[match.end() :].startswith(
            (".md", ".yaml")
        ):
            return ident
        url = target_url(found, ident, from_dir, own_path)
        if url is None:
            return ident
        found_ids.append(ident)
        return f"[{ident}]({url})"

    return TOKEN.sub(replace, line)


def link_lines(
    text: str, found: dict, from_dir: str, own_path: str, found_ids: list
) -> str:
    lines = text.split("\n")
    flags = skipped(lines)
    out = []
    inside = False
    for line, flag in zip(lines, flags):
        if flag:
            out.append(line)
            continue
        spans, inside = comment_spans(line, inside)
        if line.startswith("#") or ID_LINE.match(line.strip()):
            out.append(line)
            continue
        spans = spans + [match.span() for match in SPANS.finditer(line)]
        out.append(link_line(line, found, from_dir, own_path, spans, found_ids))
    return "\n".join(out)


CODE_SPAN = re.compile(r"(`+)(?:.+?)(?<!`)\1(?!`)")


def unlink_line(line: str) -> str:
    """Unlink the ids of one line, and leave each code span as it is."""
    out = []
    last = 0
    for match in CODE_SPAN.finditer(line):
        out.append(LINKED_ID.sub(r"\1", line[last : match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(LINKED_ID.sub(r"\1", line[last:]))
    return "".join(out)


def unlink(text: str) -> str:
    """Turn a link whose text is an id back into the bare id.

    A link in a code span or in a fenced block is an example. It stays.
    """
    lines = text.split("\n")
    flags = skipped(lines, front=False)
    return "\n".join(
        line if flag else unlink_line(line) for line, flag in zip(lines, flags)
    )


def link_text(text: str, found: dict, from_dir: str, own_path: str = "") -> str:
    return link_lines(unlink(text), found, from_dir, own_path, [])


def anchor_rows(text: str) -> str:
    """Make the first cell of each id row an anchor and the id."""
    lines = text.split("\n")
    flags = skipped(lines)
    for index, line in enumerate(lines):
        match = None if flags[index] else ROW.match(line)
        if match:
            ident = match.group(2)
            cell = f'{match.group(1)} <a id="{ident.lower()}"></a>{ident} |'
            lines[index] = cell + line[match.end() :]
    return "\n".join(lines)


def targets(root: Path) -> dict[str, tuple[str, str]]:
    """Each defined id, with its file and anchor. A deleted id has no target."""
    docs = root / "docs"
    found: dict[str, tuple[str, str]] = {}
    if not docs.is_dir():
        return found
    for path in table_paths(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = ROW.match(line)
            if match:
                found.setdefault(match.group(2), (relative, match.group(2).lower()))
    for path in sorted(docs.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        for line, flag in zip(lines, skipped(lines, front=False)):
            match = None if flag else ID_LINE.match(line.strip())
            if match is None:
                continue
            if WHOLE.fullmatch(match.group(1)):
                found.setdefault(match.group(1), (relative, ""))
    return found


def prepared(root: Path, path: Path, text: str) -> str:
    if path in table_paths(root):
        return anchor_rows(text)
    return text


def markdown_files(root: Path) -> list[Path]:
    docs = root / "docs"
    return sorted(docs.rglob("*.md")) if docs.is_dir() else []


def rewrite(root: Path) -> list[str]:
    """Write the anchors and the links. Return the paths that changed."""
    found = targets(root)
    changed = []
    for path in markdown_files(root):
        relative = path.relative_to(root).as_posix()
        old = path.read_text(encoding="utf-8")
        new = link_text(
            prepared(root, path, old), found, posixpath.dirname(relative), relative
        )
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed.append(relative)
    return sorted(changed)


def problems(root: Path) -> list[str]:
    """One message for each file that rewrite would change."""
    found = targets(root)
    errors = []
    for path in markdown_files(root):
        relative = path.relative_to(root).as_posix()
        old = path.read_text(encoding="utf-8")
        directory = posixpath.dirname(relative)
        new = link_text(prepared(root, path, old), found, directory, relative)
        if new == old:
            continue
        errors.append(f"{relative}: run make links")
        loose: list[str] = []
        link_lines(old, found, directory, relative, loose)
        if loose:
            listed = ", ".join(dict.fromkeys(loose[:5]))
            errors.append(f"{relative}: id without a link: {listed}")
    return errors


def main(argv: list[str]) -> int:
    root = repo_root(Path.cwd())
    if len(argv) >= 2 and argv[1] == "check":
        errors = problems(root)
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    for relative in rewrite(root):
        print(relative)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
