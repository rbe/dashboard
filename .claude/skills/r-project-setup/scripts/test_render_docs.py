#!/usr/bin/env python3
"""The docs renderer: Markdown under docs/ becomes HTML pages and an index page."""

# id: R-125

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("render_docs", HERE / "render_docs.py")
render_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_docs)


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(argv):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
        code = render_docs.main(argv)
    return code, out.getvalue(), err.getvalue()


class MarkdownTest(unittest.TestCase):
    def test_heading_levels(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.render_markdown("# One\n\n### Three"),
            "<h1>One</h1>\n<h3>Three</h3>",
        )

    def test_paragraph_joins_lines(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.render_markdown("a\nb\n\nc"), "<p>a b</p>\n<p>c</p>"
        )

    def test_unordered_list(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.render_markdown("- one\n- two"),
            "<ul>\n<li>one</li>\n<li>two</li></ul>",
        )

    def test_ordered_list(self):
        """id: R-125"""
        body = render_docs.render_markdown("1. one\n2. two")
        self.assertTrue(body.startswith("<ol>"))
        self.assertIn("<li>two</li>", body)

    def test_nested_list_sits_inside_the_item(self):
        """id: R-125"""
        body = render_docs.render_markdown("- outer\n  1. inner\n- next")
        self.assertEqual(
            body, "<ul>\n<li>outer\n<ol>\n<li>inner</li></ol></li>\n<li>next</li></ul>"
        )

    def test_list_item_continuation_line(self):
        """id: R-125"""
        self.assertIn("<li>one two</li>", render_docs.render_markdown("- one\n  two"))

    def test_fenced_code_is_escaped(self):
        """id: R-125"""
        body = render_docs.render_markdown("```\n<script>alert(1)</script>\n```")
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)
        self.assertTrue(body.startswith("<pre><code>"))

    def test_unclosed_fence_ends_at_end_of_file(self):
        """id: R-125"""
        self.assertTrue(
            render_docs.render_markdown("```\ncode").endswith("</code></pre>")
        )

    def test_table_with_alignment(self):
        """id: R-125"""
        body = render_docs.render_markdown("| A | B |\n|:--|--:|\n| 1 | 2 |")
        self.assertIn('<th style="text-align: left">A</th>', body)
        self.assertIn('<td style="text-align: right">2</td>', body)
        self.assertIn("<thead>", body)

    def test_blockquote(self):
        """id: R-125"""
        body = render_docs.render_markdown("> quoted **text**\n> more")
        self.assertEqual(
            body,
            "<blockquote>\n<p>quoted <strong>text</strong> more</p>\n</blockquote>",
        )

    def test_rule(self):
        """id: R-125"""
        self.assertEqual(render_docs.render_markdown("---"), "<hr>")

    def test_inline_code_is_not_emphasised(self):
        """id: R-125"""
        self.assertEqual(render_docs.inline("`a*b*c`"), "<code>a*b*c</code>")

    def test_bold_and_italic(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.inline("**b** and *i* and _j_"),
            "<strong>b</strong> and <em>i</em> and <em>j</em>",
        )

    def test_snake_case_is_not_italic(self):
        """id: R-125"""
        self.assertEqual(render_docs.inline("a_b_c"), "a_b_c")

    def test_link_md_href_becomes_html_and_keeps_fragment(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.inline("[x](../adr/0005.md#start)"),
            '<a href="../adr/0005.html#start">x</a>',
        )

    def test_external_and_fragment_links_stay(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.rewrite_href("https://example.test/a.md"),
            "https://example.test/a.md",
        )
        self.assertEqual(render_docs.rewrite_href("#top"), "#top")

    def test_scriptable_scheme_is_dropped(self):
        """id: R-125"""
        self.assertEqual(render_docs.rewrite_href("javascript:alert(1)"), "")

    def test_html_is_escaped(self):
        """id: R-125"""
        self.assertEqual(render_docs.inline("a <b> & c"), "a &lt;b&gt; &amp; c")

    def test_quote_in_href_is_escaped(self):
        """id: R-125"""
        self.assertIn("&quot;", render_docs.inline('[x](a"b)'))

    def test_image(self):
        """id: R-125"""
        self.assertEqual(
            render_docs.inline("![alt](a.png)"), '<img src="a.png" alt="alt">'
        )


class FrontmatterTest(unittest.TestCase):
    def test_frontmatter_is_stripped_and_title_read(self):
        """id: R-125"""
        fields, body = render_docs.split_frontmatter(
            "---\ntitle: My Page\nx: 1\n---\n# Heading\n"
        )
        self.assertEqual(fields["title"], "My Page")
        self.assertEqual(body.strip(), "# Heading")

    def test_text_without_frontmatter_is_unchanged(self):
        """id: R-125"""
        self.assertEqual(render_docs.split_frontmatter("# A\n"), ({}, "# A\n"))

    def test_title_order(self):
        """id: R-125"""
        self.assertEqual(render_docs.title_of({"title": "F"}, "# H", "stem"), "F")
        self.assertEqual(render_docs.title_of({}, "# `H` *x*", "stem"), "H x")
        self.assertEqual(render_docs.title_of({}, "text", "stem"), "stem")


class TreeTest(unittest.TestCase):
    def render(self, files, *extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, text in files.items():
            write(root, f"docs/{name}", text)
        code, out, err = run([str(root / "docs"), str(root / "build/docs"), *extra])
        return root, code, out, err

    def test_pages_keep_their_relative_path(self):
        """id: R-125"""
        root, code, out, _ = self.render(
            {"guide/start.md": "# Start\n\nHello `there`.\n\n- one\n"}
        )
        page = (root / "build/docs/guide/start.html").read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertIn("<title>Start</title>", page)
        self.assertIn("<code>there</code>", page)
        self.assertIn('href="../index.html"', page)
        self.assertIn("rendered 2 HTML files", out)

    def test_index_lists_every_page_with_its_title(self):
        """id: R-125"""
        root, *_ = self.render({"a.md": "# Alpha\n", "sub/b.md": "# Beta\n"})
        index = (root / "build/docs/index.html").read_text(encoding="utf-8")
        self.assertIn('<a href="a.html">Alpha</a>', index)
        self.assertIn('<a href="sub/b.html">Beta</a>', index)

    def test_own_index_page_is_kept(self):
        """id: R-125"""
        root, *_ = self.render({"index.md": "# Mine\n", "a.md": "# A\n"})
        index = (root / "build/docs/index.html").read_text(encoding="utf-8")
        self.assertIn("<h1>Mine</h1>", index)

    def test_dot_files_and_other_files_are_skipped(self):
        """id: R-125"""
        root, *_ = self.render(
            {".hidden.md": "# H\n", ".dir/x.md": "# X\n", "a.md": "# A\n", "b.txt": "t"}
        )
        names = sorted(p.name for p in (root / "build/docs").rglob("*.html"))
        self.assertEqual(names, ["a.html", "index.html"])

    def test_markdown_suffix(self):
        """id: R-125"""
        root, *_ = self.render({"a.markdown": "# A\n"})
        self.assertTrue((root / "build/docs/a.html").exists())

    def test_options_set_language_and_index_title(self):
        """id: R-125"""
        root, *_ = self.render(
            {"a.md": "# A\n"}, "--lang", "de", "--index-title", "Dokumentation"
        )
        index = (root / "build/docs/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="de">', index)
        self.assertIn("<h1>Dokumentation</h1>", index)

    def test_stale_output_is_removed(self):
        """id: R-125"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        write(root, "docs/a.md", "# A\n")
        write(root, "out/old.html", "old")
        run(["--source", str(root / "docs"), "--out", str(root / "out")])
        self.assertFalse((root / "out/old.html").exists())
        self.assertTrue((root / "out/a.html").exists())

    def test_flag_form_matches_positional_form(self):
        """id: R-125"""
        arguments = render_docs.parse_arguments(["--source", "s", "--out", "o"])
        self.assertEqual((arguments.source, arguments.out), ("s", "o"))
        defaults = render_docs.parse_arguments([])
        self.assertEqual((defaults.source, defaults.out), ("docs", "build/docs"))

    def test_missing_source_writes_nothing_and_succeeds(self):
        """id: R-125"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        code, _, err = run([str(root / "missing"), str(root / "out")])
        self.assertEqual(code, 0)
        self.assertIn("nothing to render", err)
        self.assertFalse((root / "out").exists())

    def test_output_that_holds_the_source_is_refused(self):
        """id: R-125"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        write(root, "docs/a.md", "# A\n")
        with self.assertRaises(SystemExit):
            run([str(root / "docs"), str(root)])
        self.assertTrue((root / "docs/a.md").exists())


if __name__ == "__main__":
    unittest.main()
