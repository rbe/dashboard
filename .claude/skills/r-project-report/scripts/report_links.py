#!/usr/bin/env python3
"""Links from the generated report in build/ to the documents in docs/."""

import re

ID = r"(?:ADR-\d{4}|H-\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]-\d+)"
TOKEN = re.compile(rf"(?<![A-Za-z0-9-]){ID}(?![A-Za-z0-9-])")
LINKED_ID = re.compile(rf"\[({ID})\]\([^)\s]*\)")
CODE = re.compile(r"(`+)(?:.+?)(?<!`)\1(?!`)")
TABLES = {"W": "ROADMAP.md"}
FILES = {"ADR": "adr", "H": "history", "P": "proposals"}


def source(ident: str, path: str = "") -> str:
    """The path of the document that defines an id, relative to build/.

    A requirement row stands in one of several files, so the caller gives
    the repository path of the file that holds the row.
    """
    prefix = ident.split("-", 1)[0]
    if prefix == "R" and path:
        return f"../{path}#{ident.lower()}"
    if prefix in TABLES:
        return f"../docs/{TABLES[prefix]}#{ident.lower()}"
    return f"../docs/{FILES.get(prefix, 'history')}/{ident}.md"


def link(ident: str, path: str = "") -> str:
    return f"[{ident}]({source(ident, path)})"


def unlink(text: str) -> str:
    return LINKED_ID.sub(r"\1", text)


def link_plain(text: str, known) -> str:
    paths = known if isinstance(known, dict) else {}
    return TOKEN.sub(
        lambda m: (
            link(m.group(), paths.get(m.group(), ""))
            if m.group() in known
            else m.group()
        ),
        text,
    )


def link_text(text: str, known) -> str:
    """Link each known id outside a code span. Old links are removed first.

    `known` is a set of ids, or a dict from an id to the path of its file.
    """
    text = unlink(text)
    out = []
    position = 0
    for match in CODE.finditer(text):
        out.append(link_plain(text[position : match.start()], known))
        out.append(match.group())
        position = match.end()
    out.append(link_plain(text[position:], known))
    return "".join(out)
