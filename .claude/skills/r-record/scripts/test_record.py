#!/usr/bin/env python3
"""Tests for the id check and the ADR index."""

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
ids = load("ids", HERE / "ids.py")
links = load("links", HERE / "links.py")
requirements_index = load("requirements_index", HERE / "requirements_index.py")
adr_index = load("adr_index", HERE / "adr_index.py")


class IdsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "adr").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_duplicate_id_fails(self):
        """id: R-13"""
        body = "---\nid: H-2026-11-15-one\nstatus: open\n---\n\n# One\n"
        self.write("docs/history/a.md", body)
        self.write("docs/history/b.md", body)
        errors = ids.check(self.root)
        self.assertTrue(any("H-2026-11-15-one is used 2 times" in e for e in errors))

    def test_a_live_id_above_its_counter_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "P: 1\n")
        self.write("docs/proposals/P-2.md", "---\nid: P-2\nstatus: open\n---\n")
        errors = ids.check(self.root)
        self.assertTrue(any("P-2 is above the counter P: 1" in e for e in errors))

    def test_a_live_id_of_a_kind_with_no_counter_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "R: 5\n")
        self.write("docs/proposals/P-1.md", "---\nid: P-1\nstatus: open\n---\n")
        errors = ids.check(self.root)
        self.assertTrue(any("P-1 has no counter" in error for error in errors))

    def test_a_counter_may_stand_above_the_highest_live_id(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "P: 9\n")
        self.write("docs/proposals/P-2.md", "---\nid: P-2\nstatus: open\n---\n")
        self.assertEqual(ids.check(self.root), [])

    def test_a_roadmap_row_is_a_live_id_and_a_roadmap_list_may_name_it(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "W: 1\n")
        self.write(
            "docs/ROADMAP.md",
            "| Id | Kind | Title | Proposal |\n| --- | --- | --- | --- |\n"
            "| W-1 | defect | One. | |\n",
        )
        self.write("docs/history/H-1.md", "---\nid: H-1\nroadmap: [W-1]\n---\n")
        self.assertEqual(ids.check(self.root), [])

    def test_a_list_may_name_an_id_whose_row_is_gone(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "W: 9\n")
        self.write("docs/history/H-1.md", "---\nid: H-1\nroadmap: [W-5]\n---\n")
        self.assertEqual(ids.check(self.root), [])

    def test_a_list_that_names_an_id_above_its_counter_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "W: 4\n")
        self.write("docs/history/H-1.md", "---\nid: H-1\nroadmap: [W-5]\n---\n")
        errors = ids.check(self.root)
        self.assertTrue(
            any("W-5: W-5 is above the counter W: 4" in error for error in errors)
        )

    def test_a_list_that_is_text_or_has_no_brackets_fails(self):
        """id: R-13"""
        self.write(
            "docs/history/H-1.md",
            "---\nid: H-1\nadrs: none\nroadmap: [W-1, text]\nissues:\n---\n",
        )
        errors = ids.check(self.root)
        self.assertTrue(any("adrs is not a list" in error for error in errors))
        self.assertTrue(any("issues is not a list" in error for error in errors))
        self.assertTrue(any("text, which is not an id" in error for error in errors))

    def test_a_line_that_is_not_a_counter_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "retired:\n- D-1\nR: 1\nR: 2\n")
        errors = ids.check(self.root)
        self.assertTrue(any("ids.yaml:1 is not a counter" in e for e in errors))
        self.assertTrue(any("ids.yaml:2 is not a counter" in e for e in errors))
        self.assertTrue(
            any("ids.yaml:4 has a second counter for R" in e for e in errors)
        )

    def test_an_adr_with_a_version_key_or_a_date_key_fails(self):
        """id: R-152"""
        self.write("docs/ids.yaml", "ADR: 2\n")
        self.write(
            "docs/adr/0001-one.md",
            "---\nid: ADR-0001\nstatus: Accepted\nversion: 2\ndate: 2026-11-27\n---\n",
        )
        errors = ids.check(self.root)
        self.assertTrue(
            any("0001-one.md:4 an ADR has no version key" in e for e in errors)
        )
        self.assertTrue(
            any("0001-one.md:5 an ADR has no date key" in e for e in errors)
        )

    def test_an_adr_status_must_be_accepted_or_superseded(self):
        """id: R-152"""
        self.write("docs/ids.yaml", "ADR: 3\n")
        self.write("docs/adr/ADR-0001.md", "---\nid: ADR-0001\nstatus: Accepted\n---\n")
        self.write(
            "docs/adr/ADR-0002.md", "---\nid: ADR-0002\nstatus: Superseded\n---\n"
        )
        self.write("docs/adr/template.md", "---\nid: ADR-0003\nstatus: Proposed\n---\n")
        errors = ids.check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("template.md:3 status is Proposed", errors[0])

    def test_next_id_raises_the_counter_and_never_gives_a_number_twice(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "R: 7\nW: 5\nADR: 14\nP: 0\n")
        path = self.root / "docs" / "ids.yaml"
        self.assertEqual(ids.next_id(self.root, "W"), ("W-6", []))
        self.assertEqual(ids.next_id(self.root, "W"), ("W-7", []))
        self.assertEqual(ids.next_id(self.root, "ADR"), ("ADR-0015", []))
        self.assertEqual(
            path.read_text(encoding="utf-8"), "R: 7\nW: 7\nADR: 15\nP: 0\n"
        )
        self.assertEqual(ids.check(self.root), [])

    def test_next_id_starts_above_the_highest_live_id_when_no_file_exists(self):
        """id: R-13"""
        self.write(
            "docs/requirements/record.md",
            "| Id | T | S |\n| --- | --- | --- |\n| R-3 | One | Two. |\n",
        )
        self.assertEqual(ids.next_id(self.root, "R"), ("R-4", []))
        path = self.root / "docs" / "ids.yaml"
        self.assertEqual(path.read_text(encoding="utf-8"), "R: 4\nW: 0\nADR: 0\nP: 0\n")
        self.assertEqual(ids.check(self.root), [])

    def test_next_id_refuses_a_kind_with_no_counter(self):
        """id: R-13"""
        for kind in ("H", "X"):
            ident, errors = ids.next_id(self.root, kind)
            self.assertIsNone(ident)
            self.assertTrue(errors)
        self.assertFalse((self.root / "docs" / "ids.yaml").exists())

    def test_raise_counter_sets_a_kind_and_never_lowers_it(self):
        """id: R-13"""
        self.assertEqual(ids.raise_counter(self.root, "D", 24), [])
        self.assertEqual(ids.next_id(self.root, "D"), ("D-25", []))
        errors = ids.raise_counter(self.root, "D", 25)
        self.assertTrue(any("not below 25" in error for error in errors))
        self.assertTrue(ids.raise_counter(self.root, "d", 3))
        path = self.root / "docs" / "ids.yaml"
        self.assertEqual(
            path.read_text(encoding="utf-8"), "D: 25\nR: 0\nW: 0\nADR: 0\nP: 0\n"
        )


skill_index = load("skill_index", HERE / "skill_index.py")


class SkillIndexTest(unittest.TestCase):
    def test_rows_come_from_kind_and_installed_skills_win(self):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundled = root / "skills" / "jvm"
            bundled.mkdir(parents=True)
            (bundled / "SKILL.md").write_text(
                "---\nname: jvm\nkind: language\nfiles: [java]\n---\n", encoding="utf-8"
            )
            installed = root / ".claude" / "skills" / "node"
            installed.mkdir(parents=True)
            (installed / "SKILL.md").write_text(
                "---\nname: node\nkind: language\nfiles: [js, ts]\n"
                "stages: [r-develop]\n---\n",
                encoding="utf-8",
            )
            check = root / ".claude" / "skills" / "security"
            check.mkdir(parents=True)
            (check / "SKILL.md").write_text(
                "---\nname: security\nkind: check\norder: 10\n"
                "stages: [r-plan, r-review]\n---\n",
                encoding="utf-8",
            )
            plain = root / ".claude" / "skills" / "plan"
            plain.mkdir(parents=True)
            (plain / "SKILL.md").write_text(
                "---\nname: plan\ndescription: Grill.\n---\n", encoding="utf-8"
            )
            found = skill_index.rows(root)
            self.assertEqual([row["name"] for row in found], ["security", "node"])
            text = skill_index.render(found)
            self.assertIn("skill_index[2]{name,kind,order,files,names,stages}:", text)
            self.assertIn("security,check,10,,,r-plan;r-review", text)
            self.assertIn("node,language,,js;ts,,r-develop", text)
            self.assertNotIn("jvm", text)
            self.assertNotIn("Grill", text)


class AdrIndexTest(unittest.TestCase):
    def test_index_lists_adr_links_and_not_skill_prose(self):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adr = root / "docs" / "adr"
            adr.mkdir(parents=True)
            (adr / "ADR-0004.md").write_text(
                "---\nid: ADR-0004\ntitle: Listen on localhost\nstatus: Accepted\n"
                "adrs: [ADR-0001]\nskills: [security, review]\nroadmap: [W-12]\n---\n\n# Body\n",
                encoding="utf-8",
            )
            text = adr_index.render(adr_index.rows(adr))
            self.assertIn("adr_index[1]{id,status,title,adrs,skills,roadmap}:", text)
            self.assertIn(
                "ADR-0004,Accepted,Listen on localhost,ADR-0001,security;review,W-12",
                text,
            )
            self.assertNotIn("Body", text)


toon = load("toon", HERE / "toon.py")


class IndexTargetTest(unittest.TestCase):
    def test_a_requirements_list_is_indexed_without_an_adr_directory(self):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            (docs / "requirements").mkdir(parents=True)
            (docs / "requirements" / "record.md").write_text(
                "| Id | Title | Statement |\n| --- | --- | --- |\n"
                "| R-1 | One, two | The long statement. |\n",
                encoding="utf-8",
            )
            toon.write_indexes(root)
            text = (docs / "requirements-index.toon").read_text(encoding="utf-8")
            self.assertIn("requirements[1]{id,title,status,file,owner}:", text)
            self.assertIn(
                'R-1,"One, two",in force,docs/requirements/record.md,record', text
            )
            self.assertNotIn("The long statement.", text)
            self.assertFalse((docs / "adr").exists())
            self.assertTrue((docs / "skill-index.toon").is_file())

    def test_the_index_shows_which_rows_are_planned(self):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            (docs / "requirements").mkdir(parents=True)
            (docs / "requirements" / "record.md").write_text(
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                "| R-1 | One | in force | A statement. |\n",
                encoding="utf-8",
            )
            (docs / "requirements" / "plan.md").write_text(
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                "| R-2 | Two | planned | Open work. |\n",
                encoding="utf-8",
            )
            toon.write_indexes(root)
            text = (docs / "requirements-index.toon").read_text(encoding="utf-8")
            self.assertIn("R-1,One,in force,docs/requirements/record.md,record", text)
            self.assertIn("R-2,Two,planned,docs/requirements/plan.md,plan", text)

    def test_a_product_repository_still_gets_an_adr_index(self):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            toon.write_indexes(root)
            index = root / "docs" / "adr" / "index.toon"
            self.assertTrue(index.is_file())
            self.assertIn("adr_index[0]", index.read_text(encoding="utf-8"))
            self.assertFalse((root / "docs" / "requirements-index.toon").exists())

    def test_adr_files_keep_the_adr_index_when_a_requirements_list_is_also_present(
        self,
    ):
        """id: R-6"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adr = root / "docs" / "adr"
            adr.mkdir(parents=True)
            (adr / "ADR-0004.md").write_text(
                "---\nid: ADR-0004\ntitle: Listen\nstatus: Accepted\n---\n",
                encoding="utf-8",
            )
            (root / "docs" / "requirements").mkdir()
            (root / "docs" / "requirements" / "record.md").write_text(
                "| Id | Statement |\n| --- | --- |\n| R-1 | One. |\n",
                encoding="utf-8",
            )
            toon.write_indexes(root)
            text = (adr / "index.toon").read_text(encoding="utf-8")
            self.assertIn("ADR-0004,Accepted,Listen,,,", text)
            self.assertFalse((root / "docs" / "requirements-index.toon").exists())


skill_index = load("skill_index", HERE / "skill_index.py")


def write_file(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class SkillNameTest(unittest.TestCase):
    def test_a_skill_name_that_differs_from_its_directory_is_an_error(self):
        """id: R-4"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "skills/plan/SKILL.md", "---\nname: plan\n---\n")
            self.assertEqual(skill_index.name_errors(root), [])
            write_file(root, "skills/review/SKILL.md", "---\nname: check\n---\n")
            errors = skill_index.name_errors(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("review", errors[0])

    def test_make_toon_fails_when_a_skill_name_differs(self):
        """id: R-4"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            write_file(root, "skills/review/SKILL.md", "---\nname: check\n---\n")
            previous = Path.cwd()
            try:
                os.chdir(root)
                self.assertEqual(toon.main(), 1)
                write_file(root, "skills/review/SKILL.md", "---\nname: review\n---\n")
                self.assertEqual(toon.main(), 0)
            finally:
                os.chdir(previous)
            self.assertTrue((root / "docs" / "skill-index.toon").is_file())

    def test_a_description_with_a_colon_and_a_space_is_an_error(self):
        """id: R-65"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "skills/plan/SKILL.md",
                "---\nname: plan\ndescription: Grill a change. Ask one question.\n---\n",
            )
            self.assertEqual(skill_index.yaml_errors(root), [])
            write_file(
                root,
                "skills/security/SKILL.md",
                '---\nname: security\ndescription: Write "security: not installed".\n---\n',
            )
            errors = skill_index.yaml_errors(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("security", errors[0])
            self.assertIn("description", errors[0])

    def test_every_skill_in_this_collection_has_yaml_frontmatter(self):
        """id: R-65"""
        self.assertEqual(skill_index.yaml_errors(HERE.parents[2]), [])

    def test_every_skill_in_this_collection_has_its_directory_name(self):
        """id: R-4"""
        self.assertEqual(skill_index.name_errors(HERE.parents[2]), [])


class TableIdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_known_issue_row_is_a_live_id(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "W: 1\nR: 1\n")
        self.write(
            "docs/ROADMAP.md",
            "| Id | Defect |\n| --- | --- |\n| W-1 | One. |\n",
        )
        self.assertEqual(ids.check(self.root), [])
        self.write("docs/history/extra.md", "---\nid: W-1\n---\n")
        self.assertTrue(any("W-1" in error for error in ids.check(self.root)))

    def test_a_requirements_file_of_the_old_single_path_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "R: 1\n")
        self.write(
            "docs/REQUIREMENTS.md",
            "| Id | Statement |\n| --- | --- |\n| R-1 | One. |\n",
        )
        errors = ids.check(self.root)
        self.assertTrue(any("move its rows to docs/requirements/" in e for e in errors))

    def test_a_table_id_is_live_and_a_repeat_fails(self):
        """id: R-13"""
        self.write("docs/ids.yaml", "W: 1\nR: 1\n")
        self.write(
            "docs/requirements/record.md",
            "| Id | Statement |\n| --- | --- |\n| R-1 | One. |\n",
        )
        self.write(
            "docs/ROADMAP.md",
            "| Id | Kind | Title |\n| --- | --- | --- |\n| W-1 | Open | Later. |\n",
        )
        self.assertEqual(ids.check(self.root), [])
        self.write("docs/history/extra.md", "---\nid: R-1\n---\n")
        errors = ids.check(self.root)
        self.assertTrue(any("R-1" in error for error in errors))


ANCHORED = '| Id | Kind | Title |\n| --- | --- | --- |\n| <a id="w-9"></a>W-9 | feature | See R-1. |\n'


def tree(root, files):
    for relative, text in files.items():
        write_file(root, relative, text)


class LinkTest(unittest.TestCase):
    def test_a_link_in_a_code_span_or_a_code_block_is_an_example_and_stays(self):
        """id: R-69"""
        found = {"W-9": ("docs/ROADMAP.md", "w-9")}
        text = (
            "The form is `[W-9](../ROADMAP.md#w-9)`. See [W-9](wrong.md).\n"
            "```\n[W-9](example.md)\n```\n"
        )
        result = links.link_text(text, found, "docs/history")
        self.assertIn("`[W-9](../ROADMAP.md#w-9)`", result)
        self.assertIn("See [W-9](../ROADMAP.md#w-9).", result)
        self.assertIn("```\n[W-9](example.md)\n```", result)
        self.assertEqual(
            links.unlink("[W-9](x.md) and `[W-9](y.md)`"), "W-9 and `[W-9](y.md)`"
        )

    FOUND = {
        "W-9": ("docs/ROADMAP.md", "w-9"),
        "H-2026-11-20-go-skill": ("docs/history/H-2026-11-20-go-skill.md", ""),
    }

    def test_targets_cover_a_table_id_and_a_frontmatter_id_and_skip_a_deleted_id(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tree(
                root,
                {
                    "docs/ROADMAP.md": ANCHORED,
                    "docs/history/H-2026-11-20-go-skill.md": "---\nid: H-2026-11-20-go-skill\n---\n",
                    "docs/ids.yaml": "W: 9\n",
                },
            )
            found = links.targets(root)
            self.assertEqual(found["W-9"], ("docs/ROADMAP.md", "w-9"))
            self.assertEqual(
                found["H-2026-11-20-go-skill"],
                ("docs/history/H-2026-11-20-go-skill.md", ""),
            )
            self.assertNotIn("W-1", found)

    def test_link_text_links_a_prose_id_with_a_relative_path(self):
        """id: R-69"""
        text = links.link_text(
            "See W-9 and H-2026-11-20-go-skill.", self.FOUND, "docs/history"
        )
        self.assertEqual(
            text,
            "See [W-9](../ROADMAP.md#w-9) and "
            "[H-2026-11-20-go-skill](H-2026-11-20-go-skill.md).",
        )
        self.assertEqual(
            links.link_text("W-9", self.FOUND, "build"),
            "[W-9](../docs/ROADMAP.md#w-9)",
        )
        self.assertEqual(
            links.link_text("W-9", self.FOUND, "docs", "docs/ROADMAP.md"),
            "[W-9](#w-9)",
        )

    def test_link_text_leaves_code_links_comments_frontmatter_headings_and_cells(self):
        """id: R-69"""
        cases = [
            "A `W-9` span.",
            "```\nW-9\n```",
            "A [see W-9](https://example.com/W-9) link.",
            "---\nid: W-9\ntitle: W-9\n---",
            "# Heading W-9",
            "<!-- W-9 -->",
            "<!--\nW-9\n-->",
            "| W-9 | text |",
            "| Id | W-9 |\n| W-9 | text |",
            "Path docs/history/W-9.md here.",
        ]
        for case in cases:
            with self.subTest(case=case):
                text = links.link_text(case, self.FOUND, "docs")
                self.assertEqual(
                    text.replace("| Id | [W-9](ROADMAP.md#w-9) |", "| Id | W-9 |"),
                    case,
                )

    def test_link_text_links_a_later_cell_and_leaves_an_unknown_id_plain(self):
        """id: R-69"""
        text = links.link_text("| R-2 | W-9 and W-77 |", self.FOUND, "docs")
        self.assertEqual(text, "| R-2 | [W-9](ROADMAP.md#w-9) and W-77 |")

    def test_unlink_restores_the_bare_id_and_keeps_other_links(self):
        """id: R-69"""
        text = "[W-9](../ROADMAP.md#w-9) and [docs](a.md) and [W-9 here](b.md)"
        self.assertEqual(
            links.unlink(text), "W-9 and [docs](a.md) and [W-9 here](b.md)"
        )
        linked = links.link_text(text, self.FOUND, "docs/history")
        self.assertEqual(links.unlink(linked), links.unlink(text))

    def test_anchor_rows_adds_the_anchor_once(self):
        """id: R-69"""
        row = "| W-9 | feature | One. |"
        once = links.anchor_rows(row)
        self.assertEqual(once, '| <a id="w-9"></a>W-9 | feature | One. |')
        self.assertEqual(links.anchor_rows(once), once)
        self.assertEqual(links.strip_anchor('<a id="w-9"></a>W-9 '), "W-9")
        self.assertEqual(links.anchor_rows("| Id | Status |"), "| Id | Status |")

    def sample(self, root):
        tree(
            root,
            {
                "docs/ROADMAP.md": "# Roadmap\n\n| Id | Kind | Title |\n| --- | --- | --- |\n"
                "| W-9 | feature | W-9 and R-1 and W-1. |\n",
                "docs/requirements/record.md": "| Id | Title | Statement |\n| --- | --- | --- |\n"
                "| R-1 | One | See W-9. |\n",
                "docs/history/H-2026-11-20-x.md": "---\nid: H-2026-11-20-x\n---\n\n# X\n\nSee W-9 and `R-1`.\n",
                "docs/ids.yaml": "W: 9\nR: 1\n",
            },
        )

    def test_rewrite_changes_files_once_and_does_not_link_a_row_to_itself(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            changed = links.rewrite(root)
            self.assertEqual(
                changed,
                [
                    "docs/ROADMAP.md",
                    "docs/history/H-2026-11-20-x.md",
                    "docs/requirements/record.md",
                ],
            )
            roadmap = (root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
            self.assertIn(
                '| <a id="w-9"></a>W-9 | feature | W-9 and [R-1](requirements/record.md#r-1) and W-1. |',
                roadmap,
            )
            history = (root / "docs/history/H-2026-11-20-x.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("See [W-9](../ROADMAP.md#w-9) and `R-1`.", history)
            self.assertEqual(links.rewrite(root), [])

    def test_problems_report_an_unlinked_id_and_none_after_rewrite(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            errors = links.problems(root)
            self.assertIn("docs/history/H-2026-11-20-x.md: run make links", errors)
            self.assertTrue(any("without a link: W-9" in error for error in errors))
            links.rewrite(root)
            self.assertEqual(links.problems(root), [])

    def test_a_row_links_to_a_row_in_another_requirement_file(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = "| Id | Title | Statement |\n| --- | --- | --- |\n"
            tree(
                root,
                {
                    "docs/requirements/plan.md": header + "| R-1 | One | See R-2. |\n",
                    "docs/requirements/record.md": header
                    + "| R-2 | Two | See R-1. |\n",
                    "docs/ids.yaml": "R: 2\n",
                },
            )
            links.rewrite(root)
            plan = (root / "docs/requirements/plan.md").read_text(encoding="utf-8")
            record = (root / "docs/requirements/record.md").read_text(encoding="utf-8")
            self.assertIn("See [R-2](record.md#r-2).", plan)
            self.assertIn("See [R-1](plan.md#r-1).", record)
            self.assertEqual(links.problems(root), [])

    def test_ids_check_finds_a_repeat_when_the_row_has_an_anchor(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tree(
                root,
                {
                    "docs/ROADMAP.md": ANCHORED,
                    "docs/history/extra.md": "---\nid: W-9\n---\n",
                },
            )
            self.assertTrue(any("W-9" in error for error in ids.check(root)))


req = load("req", HERE / "req.py")

HEADER = "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"


class ReqTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        tree(
            self.root,
            {
                "docs/requirements/record.md": HEADER
                + '| <a id="r-1"></a>R-1 | Ids | in force | Podman holds the ids. |\n'
                + "| R-2 | Index | planned | Write the index. |\n",
                "docs/requirements/plan.md": HEADER
                + "| R-3 | Grill | in force | Ask one question. Use PODMAN never. |\n",
            },
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_id_prints_the_whole_row(self):
        """id: R-84"""
        text, errors, code = req.run(self.root, ids="R-1")
        self.assertEqual(
            text,
            "R-1\ntitle: Ids\nstatus: in force\nfile: docs/requirements/record.md\n"
            "owner: record\nstatement: Podman holds the ids.",
        )
        self.assertEqual((errors, code), ([], 0))

    def test_two_ids_print_two_rows_and_an_unknown_id_fails(self):
        """id: R-84"""
        text, errors, code = req.run(self.root, ids="R-3 R-2")
        self.assertTrue(text.startswith("R-3\n"))
        self.assertIn("\n\nR-2\n", text)
        self.assertEqual(code, 0)
        text, errors, code = req.run(self.root, ids="R-1 R-99")
        self.assertTrue(text.startswith("R-1\n"))
        self.assertEqual((errors, code), (["req: R-99 not found"], 1))

    def test_a_word_lists_id_title_and_file_of_each_match_in_any_case(self):
        """id: R-84"""
        text, errors, code = req.run(self.root, word="podman")
        self.assertEqual(
            text.splitlines(),
            [
                "R-3 | Grill | docs/requirements/plan.md",
                "R-1 | Ids | docs/requirements/record.md",
            ],
        )
        self.assertNotIn("Podman holds", text)
        self.assertEqual(code, 0)

    def test_full_adds_the_statement_to_a_list(self):
        """id: R-84"""
        text, _, _ = req.run(self.root, word="index", full=True)
        self.assertEqual(
            text, "R-2 | Index | docs/requirements/record.md\n  Write the index."
        )

    def test_an_owner_and_a_status_list_rows_and_filters_combine(self):
        """id: R-84"""
        text, _, _ = req.run(self.root, owner="record")
        self.assertEqual(len(text.splitlines()), 2)
        text, _, _ = req.run(self.root, status="planned")
        self.assertEqual(text, "R-2 | Index | docs/requirements/record.md")
        text, _, _ = req.run(self.root, owner="plan", status="planned")
        self.assertEqual(text, "")
        _, errors, code = req.run(self.root, owner="plan", status="planned")
        self.assertEqual((errors, code), (["req: no item matches"], 1))

    def test_no_filter_or_an_id_with_a_filter_is_refused(self):
        """id: R-84"""
        self.assertEqual(req.run(self.root)[2], 2)
        self.assertEqual(req.run(self.root, ids="R-1", word="x")[2], 2)

    def test_adrs_are_read_by_id_and_by_word_and_have_no_owner(self):
        """id: R-84"""
        write_file(
            self.root,
            "docs/adr/ADR-0001.md",
            "---\nid: ADR-0001\ntitle: Listen on localhost\nstatus: Accepted\n---\n\n"
            "## Rule\n\nBind to 127.0.0.1 only.\n",
        )
        text, _, _ = req.run(self.root, ids="ADR-0001")
        self.assertIn("title: Listen on localhost", text)
        self.assertIn("file: docs/adr/ADR-0001.md", text)
        self.assertIn("Bind to 127.0.0.1 only.", text)
        self.assertNotIn("owner:", text)
        text, _, _ = req.run(self.root, word="127.0.0.1")
        self.assertEqual(text, "ADR-0001 | Listen on localhost | docs/adr/ADR-0001.md")
        text, _, _ = req.run(self.root, status="accepted")
        self.assertEqual(text, "ADR-0001 | Listen on localhost | docs/adr/ADR-0001.md")
        text, _, _ = req.run(self.root, owner="record")
        self.assertNotIn("ADR-0001", text)

    def test_main_prints_the_text_and_the_errors_and_returns_the_status(self):
        """id: R-84"""
        write_file(self.root, "docs/adr/note.md", "No frontmatter, so no id.\n")
        previous = Path.cwd()
        os.chdir(self.root)
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = req.main(["req.py", "--id", "R-3 R-99", "--full"])
            self.assertEqual(code, 1)
            self.assertTrue(out.getvalue().startswith("R-3\ntitle: Grill\n"))
            self.assertEqual(err.getvalue(), "req: R-99 not found\n")
            out = io.StringIO()
            with redirect_stdout(out):
                code = req.main(["req.py", "--q", "grill", "--full"])
            self.assertEqual(code, 0)
            self.assertIn(
                "R-3 | Grill | docs/requirements/plan.md\n  Ask", out.getvalue()
            )
        finally:
            os.chdir(previous)

    def test_the_module_finds_its_sibling_scripts_when_the_path_lacks_them(self):
        """id: R-84"""
        here = str(HERE)
        saved = list(sys.path)
        sys.path[:] = [entry for entry in sys.path if entry != here]
        sys.modules.pop("adr_index", None)
        try:
            self.assertTrue(hasattr(req.sibling("adr_index"), "frontmatter"))
        finally:
            sys.path[:] = saved

    def test_the_target_passes_each_variable_to_the_script(self):
        """id: R-84"""
        text = (HERE.parent / "index.mk").read_text(encoding="utf-8")
        for flag in ("--id", "--q", "--owner", "--status", "--full"):
            self.assertIn(flag, text)
        self.assertIn("$(origin OWNER)", text)


if __name__ == "__main__":
    unittest.main()
