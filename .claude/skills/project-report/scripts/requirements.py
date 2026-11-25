#!/usr/bin/env python3
"""Requirement ids from the board, and the id a test names."""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

ID_LINE = re.compile(r"^id:\s*[\"']?([^\"'#\s]+)")
ID_CELL = re.compile(r"^[A-Z]+-\d+$")
ANCHOR = re.compile(r'^<a id="[^"]*"></a>')
IN_FORCE = "in force"
# A test proves a rule in force. A roadmap row and a planned row are
# work. A roadmap row ends, and its number is never issued again.
PROVABLE = {"adr", "requirement"}
SKIP = {
    ".git",
    ".claude",
    ".gradle",
    ".venv",
    "__pycache__",
    "apm_modules",
    "build",
    "dist",
    "node_modules",
}
OTHER_TEST_FILE = re.compile(
    r"(?:\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)"
    r"|(?:Test|Tests|Spec|IT)\.(?:java|groovy|kt)"
    r"|_test\.go)$"
)
COMMENT_ID = re.compile(r"^(?://+|/\*+|\*|#)\s*id:\s*[\"']?([^\"'#\s*]+)")


@dataclass(frozen=True)
class Requirement:
    id: str
    kind: str
    title: str
    status: str
    path: str = ""


@dataclass(frozen=True)
class TestProof:
    requirement_id: str | None
    qualified_name: str
    path: str


def adr_markdown(root: Path) -> list[Path]:
    adr_dir = root / "docs" / "adr"
    if not adr_dir.is_dir():
        return []
    return sorted(path for path in adr_dir.glob("*.md") if path.is_file())


def requirement_files(root: Path) -> list[Path]:
    """The files of docs/requirements/, one for each skill that owns rows."""
    folder = root / "docs" / "requirements"
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def uses_requirements_list(root: Path) -> bool:
    return bool(requirement_files(root)) and not adr_markdown(root)


def strip_anchor(cell: str) -> str:
    """Remove a leading anchor from a table cell."""
    return ANCHOR.sub("", cell.strip()).strip()


def table_rows(path: Path) -> list[dict[str, str]]:
    """Each id row of a table, by the lowercase name of its column."""
    if not path.is_file():
        return []
    found = []
    header: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [part.strip() for part in stripped.strip("|").split("|")]
        first = strip_anchor(cells[0]) if cells else ""
        if first.lower() == "id":
            header = [cell.lower() for cell in cells]
            continue
        if header and ID_CELL.match(first):
            found.append(dict(zip(header, [first, *cells[1:]])))
    return found


def requirement_rows(root: Path) -> list[Requirement]:
    """The rows of the requirements list. A planned row is work, not a rule."""
    found = []
    for path in requirement_files(root):
        relative = path.relative_to(root).as_posix()
        for row in table_rows(path):
            status = row.get("status") or IN_FORCE
            kind = "planned" if status == "planned" else "requirement"
            found.append(
                Requirement(row["id"], kind, row.get("title", ""), status, relative)
            )
    return found


def roadmap_rows(root: Path) -> list[Requirement]:
    return [
        Requirement(
            row["id"],
            "roadmap",
            row.get("title", ""),
            row.get("kind", ""),
            "docs/ROADMAP.md",
        )
        for row in table_rows(root / "docs" / "ROADMAP.md")
    ]


def repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "Makefile").is_file() and (
            (candidate / "skills").is_dir()
            or (candidate / ".claude" / "skills").is_dir()
        ):
            return candidate
    return current


def requirement_id(docstring: str | None) -> str | None:
    if not docstring:
        return None
    for line in docstring.splitlines():
        match = ID_LINE.match(line.strip())
        if match:
            return match.group(1)
    return None


def split_blocks(text: str) -> list[tuple[str, str]]:
    parts = text.split("---")
    if len(parts) < 3:
        return []
    blocks = []
    rest = parts[1:]
    index = 0
    while index < len(rest):
        front = rest[index]
        body = rest[index + 1] if index + 1 < len(rest) else ""
        blocks.append((front, body))
        index += 2
    return blocks


def scalars(front: str) -> dict[str, str]:
    data = {}
    for line in front.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or line[:1] in (" ", "\t", "-"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def first_sentence(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped.lstrip("-").strip()
    return ""


def requirements_in_markdown(path: Path, kind: str) -> list[Requirement]:
    text = path.read_text(encoding="utf-8")
    found = []
    seen = set()
    for front, body in split_blocks(text):
        data = scalars(front)
        ident = data.get("id", "")
        if not ident or ident in seen:
            continue
        seen.add(ident)
        title = data.get("title") or first_sentence(body) or ident
        found.append(Requirement(ident, kind, title, data.get("status", "")))
    for line in text.splitlines():
        match = ID_LINE.match(line.strip())
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            found.append(Requirement(match.group(1), kind, match.group(1), ""))
    return found


def collect_board(root: Path) -> list[Requirement]:
    found = []
    adr_dir = root / "docs" / "adr"
    if adr_dir.is_dir():
        for path in sorted(adr_dir.glob("*.md")):
            found.extend(requirements_in_markdown(path, "adr"))
    found.extend(requirement_rows(root))
    found.extend(roadmap_rows(root))
    unique = []
    seen = set()
    for item in found:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return sorted(unique, key=lambda item: item.id)


def collect(root: Path) -> list[Requirement]:
    if uses_requirements_list(root):
        return requirement_rows(root)
    return collect_board(root)


def parents_of(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    found = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            found[child] = parent
    return found


def is_test(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if not node.name.startswith("test"):
        return False
    parent = parents.get(node)
    if isinstance(parent, ast.Module):
        return True
    return isinstance(parent, ast.ClassDef) and isinstance(
        parents.get(parent), ast.Module
    )


def proofs_in(path: Path, root: Path) -> list[TestProof]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    relative = path.relative_to(root).as_posix()
    module = (
        relative[: -len(".py")].replace("/", ".")
        if relative.endswith(".py")
        else relative
    )
    found = []
    parents = parents_of(tree)
    for node in ast.walk(tree):
        if not is_test(node, parents):
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.ClassDef):
            qualified = f"{module}.{parent.name}.{node.name}"
        else:
            qualified = f"{module}.{node.name}"
        docstring = ast.get_docstring(node, clean=True)
        found.append(TestProof(requirement_id(docstring), qualified, relative))
    return found


def test_files(root: Path) -> list[Path]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP for part in path.parts):
            continue
        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            found.append(path)
    return found


def other_test_files(root: Path) -> list[Path]:
    found = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP for part in path.parts):
            continue
        if path.is_file() and OTHER_TEST_FILE.search(path.name):
            found.append(path)
    return found


def proofs_in_comments(path: Path, root: Path) -> list[TestProof]:
    relative = path.relative_to(root).as_posix()
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = COMMENT_ID.match(line.strip())
        if match:
            found.append(TestProof(match.group(1), relative, relative))
    if not found:
        found.append(TestProof(None, relative, relative))
    return found


def proofs(root: Path) -> list[TestProof]:
    found = []
    for path in test_files(root):
        found.extend(proofs_in(path, root))
    for path in other_test_files(root):
        found.extend(proofs_in_comments(path, root))
    return found


def problems(
    requirements: list[Requirement], proofs_found: list[TestProof]
) -> list[str]:
    known = {item.id for item in requirements if item.kind in PROVABLE}
    errors = []
    for proof in proofs_found:
        if proof.requirement_id is None:
            errors.append(f"{proof.qualified_name} has no id")
        elif proof.requirement_id not in known:
            errors.append(
                f"{proof.qualified_name} names {proof.requirement_id}, which is not a requirement"
            )
    return errors
