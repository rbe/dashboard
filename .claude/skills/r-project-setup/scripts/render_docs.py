#!/usr/bin/env python3
"""Render the Markdown files under docs/ to HTML pages and an index page.

Usage: render_docs.py [SOURCE [OUT]] [--source X] [--out Y] [--lang L] [--index-title T]
Python 3 standard library only. The output keeps the relative path of each file.
"""

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

MARKDOWN_SUFFIXES = (".md", ".markdown")
IMAGE_OR_LINK_OR_CODE = re.compile(
    r"!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|`([^`]+)`"
)
BOLD = re.compile(r"\*\*([^*]+)\*\*|(?<!\w)__([^_]+)__(?!\w)")
ITALIC = re.compile(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)|(?<!\w)_([^_\s][^_]*)_(?!\w)")
STRIKE = re.compile(r"~~([^~]+)~~")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
UNSAFE_SCHEME = re.compile(r"^(javascript|vbscript|data):", re.IGNORECASE)
ANY_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def escape(text):
    return html.escape(text, quote=False)


def rewrite_href(url):
    url = url.strip()
    if UNSAFE_SCHEME.match(url):
        return ""
    if ANY_SCHEME.match(url) or url.startswith("#"):
        return url
    path, separator, fragment = url.partition("#")
    path, query_separator, query = path.partition("?")
    if path.endswith(".md"):
        path = path[:-3] + ".html"
    elif path.endswith(".markdown"):
        path = path[: -len(".markdown")] + ".html"
    return path + query_separator + query + separator + fragment


def emphasis(escaped):
    def first_group(match):
        return match.group(1) if match.group(1) is not None else match.group(2)

    text = BOLD.sub(lambda m: "<strong>" + first_group(m) + "</strong>", escaped)
    text = ITALIC.sub(lambda m: "<em>" + first_group(m) + "</em>", text)
    return STRIKE.sub(lambda m: "<del>" + m.group(1) + "</del>", text)


def plain_inline(text):
    return emphasis(escape(text))


def inline_token(match):
    if match.group(2) is not None:
        source = html.escape(rewrite_href(match.group(2)), quote=True)
        alt = html.escape(match.group(1), quote=True)
        return f'<img src="{source}" alt="{alt}">'
    if match.group(4) is not None:
        href = html.escape(rewrite_href(match.group(4)), quote=True)
        return f'<a href="{href}">{plain_inline(match.group(3))}</a>'
    return "<code>" + escape(match.group(5)) + "</code>"


def inline(text):
    pieces = []
    position = 0
    for match in IMAGE_OR_LINK_OR_CODE.finditer(text):
        pieces.append(plain_inline(text[position : match.start()]))
        pieces.append(inline_token(match))
        position = match.end()
    pieces.append(plain_inline(text[position:]))
    return "".join(pieces)


def split_frontmatter(text):
    """Return (fields, body). Fields are the plain key: value lines of the YAML block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            return frontmatter_fields(lines[1:end]), "\n".join(lines[end + 1 :])
    return {}, text


def frontmatter_fields(lines):
    fields = {}
    for line in lines:
        key, separator, value = line.partition(":")
        if separator and key.strip() and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def table_cells(line):
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return [
        cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)
    ]


def table_alignments(separator_line):
    alignments = []
    for cell in table_cells(separator_line):
        left, right = cell.startswith(":"), cell.endswith(":")
        alignments.append(
            "center" if left and right else "right" if right else "left" if left else ""
        )
    return alignments


def table_cell(tag, text, alignment):
    style = f' style="text-align: {alignment}"' if alignment else ""
    return f"<{tag}{style}>{inline(text)}</{tag}>"


def table_row(tag, cells, alignments):
    padded = cells + [""] * (len(alignments) - len(cells))
    return (
        "<tr>"
        + "".join(
            table_cell(tag, c, alignments[i])
            for i, c in enumerate(padded[: len(alignments)])
        )
        + "</tr>"
    )


def render_table(header_line, separator_line, row_lines):
    alignments = table_alignments(separator_line)
    head = table_row("th", table_cells(header_line), alignments)
    rows = [table_row("td", table_cells(line), alignments) for line in row_lines]
    parts = ["<table>", "<thead>", head, "</thead>"]
    if rows:
        parts += ["<tbody>", *rows, "</tbody>"]
    parts.append("</table>")
    return "\n".join(parts)


def starts_table(lines, index):
    return (
        "|" in lines[index]
        and index + 1 < len(lines)
        and "|" in lines[index + 1]
        and bool(TABLE_SEPARATOR.match(lines[index + 1]))
    )


def read_table(lines, index):
    rows = []
    position = index + 2
    while position < len(lines) and lines[position].strip() and "|" in lines[position]:
        rows.append(lines[position])
        position += 1
    return render_table(lines[index], lines[index + 1], rows), position


def read_code_block(lines, index):
    body = []
    position = index + 1
    while position < len(lines) and not lines[position].startswith("```"):
        body.append(html.escape(lines[position], quote=False))
        position += 1
    code = "<pre><code>" + "\n".join(body) + "</code></pre>"
    return code, min(position + 1, len(lines))


def read_blockquote(lines, index):
    quoted = []
    position = index
    while position < len(lines) and lines[position].lstrip().startswith(">"):
        text = lines[position].lstrip()[1:]
        quoted.append(text[1:] if text.startswith(" ") else text)
        position += 1
    return "<blockquote>\n" + render_markdown(
        "\n".join(quoted)
    ) + "\n</blockquote>", position


class ListWriter:
    """Writes nested lists. Each open level keeps its last item open for a nested list."""

    def __init__(self, out):
        self.out = out
        self.levels = []
        self.pending = None

    def is_open(self):
        return bool(self.levels)

    def add_item(self, indent, tag, text):
        self.flush_text()
        while self.levels and self.levels[-1][0] > indent:
            self.close_level()
        if self.levels and self.levels[-1][0] == indent and self.levels[-1][1] != tag:
            self.close_level()
        if self.levels and self.levels[-1][0] == indent:
            self.out[-1] += "</li>"
        else:
            self.out.append(f"<{tag}>")
            self.levels.append((indent, tag))
        self.out.append("<li>")
        self.pending = [text]

    def continue_item(self, text):
        if self.pending is not None:
            self.pending.append(text)

    def flush_text(self):
        if self.pending is not None:
            self.out[-1] += inline(" ".join(self.pending))
            self.pending = None

    def close_level(self):
        self.flush_text()
        _, tag = self.levels.pop()
        self.out[-1] += f"</li></{tag}>"

    def close_all(self):
        while self.levels:
            self.close_level()


def list_tag(marker):
    return "ol" if marker[0].isdigit() else "ul"


def render_markdown(text):
    lines = text.replace("\r\n", "\n").split("\n")
    out = []
    paragraph = []
    lists = ListWriter(out)

    def flush_paragraph():
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def close_blocks():
        flush_paragraph()
        lists.close_all()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            close_blocks()
            block, index = read_code_block(lines, index)
            out.append(block)
        elif not line.strip():
            close_blocks()
            index += 1
        elif HEADING.match(line):
            close_blocks()
            level, title = HEADING.match(line).groups()
            out.append(f"<h{len(level)}>{inline(title)}</h{len(level)}>")
            index += 1
        elif RULE.match(line) and not LIST_ITEM.match(line):
            close_blocks()
            out.append("<hr>")
            index += 1
        elif line.lstrip().startswith(">"):
            close_blocks()
            block, index = read_blockquote(lines, index)
            out.append(block)
        elif starts_table(lines, index):
            close_blocks()
            block, index = read_table(lines, index)
            out.append(block)
        elif LIST_ITEM.match(line):
            flush_paragraph()
            indent, marker, body = LIST_ITEM.match(line).groups()
            lists.add_item(len(indent.expandtabs(4)), list_tag(marker), body.strip())
            index += 1
        elif lists.is_open() and line[:1] in (" ", "\t"):
            lists.continue_item(line.strip())
            index += 1
        else:
            lists.close_all()
            paragraph.append(line.strip())
            index += 1
    close_blocks()
    return "\n".join(out)


def page(title, body, lang="en", home=None):
    home_link = (
        f'<p><a href="{html.escape(home, quote=True)}">Index</a></p>\n' if home else ""
    )
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{html.escape(lang, quote=True)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        "</head>\n"
        "<body>\n"
        f"{home_link}{body}\n"
        "</body>\n"
        "</html>\n"
    )


def first_heading(body):
    for line in body.splitlines():
        found = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if found:
            return re.sub(r"[`*_]", "", found.group(1)).strip()
    return ""


def title_of(fields, body, fallback):
    return fields.get("title") or first_heading(body) or fallback


def markdown_files(source):
    """The Markdown files under source, sorted. A name that starts with a dot is skipped."""
    found = []
    for path in sorted(source.rglob("*")):
        parts = path.relative_to(source).parts
        if any(part.startswith(".") for part in parts):
            continue
        if path.is_file() and path.suffix in MARKDOWN_SUFFIXES:
            found.append(path)
    return found


def html_name(relative):
    return relative.with_suffix(".html").as_posix()


def home_link(name):
    return "../" * name.count("/") + "index.html"


def render_file(path, source, dest, lang):
    fields, body = split_frontmatter(path.read_text(encoding="utf-8"))
    relative = path.relative_to(source)
    name = html_name(relative)
    title = title_of(fields, body, path.stem)
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page(title, render_markdown(body), lang, home_link(name)), encoding="utf-8"
    )
    return name, title


def index_body(index_title, pages):
    items = "\n".join(
        f'<li><a href="{html.escape(name, quote=True)}">{escape(title)}</a></li>'
        for name, title in pages
    )
    return f"<h1>{escape(index_title)}</h1>\n<ul>\n{items}\n</ul>"


def write_index(dest, index_title, pages, lang):
    body = index_body(index_title, pages)
    (dest / "index.html").write_text(page(index_title, body, lang), encoding="utf-8")


def clear_output(source, dest):
    if dest.resolve() == source.resolve() or dest.resolve() in source.resolve().parents:
        raise SystemExit(
            f"docs: the output {dest} holds the source {source}; refusing to delete it."
        )
    shutil.rmtree(dest)


def render_tree(source, dest, lang="en", index_title="Documentation"):
    source, dest = Path(source), Path(dest)
    files = markdown_files(source) if source.is_dir() else []
    if not files:
        print(
            f"docs: no Markdown files in {source}; nothing to render.", file=sys.stderr
        )
        return 0
    if dest.exists():
        clear_output(source, dest)
    pages = [render_file(path, source, dest, lang) for path in files]
    if not any(name == "index.html" for name, _ in pages):
        write_index(dest, index_title, pages, lang)
        pages.append(("index.html", index_title))
    print(f"docs: rendered {len(pages)} HTML files in {dest}")
    return 0


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="Render Markdown under docs/ to HTML.")
    parser.add_argument("source_positional", nargs="?", metavar="SOURCE")
    parser.add_argument("out_positional", nargs="?", metavar="OUT")
    parser.add_argument("--source", dest="source_flag")
    parser.add_argument("--out", dest="out_flag")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--index-title", default="Documentation")
    arguments = parser.parse_args(argv)
    arguments.source = arguments.source_flag or arguments.source_positional or "docs"
    arguments.out = arguments.out_flag or arguments.out_positional or "build/docs"
    return arguments


def main(argv):
    arguments = parse_arguments(argv)
    return render_tree(
        arguments.source, arguments.out, arguments.lang, arguments.index_title
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
