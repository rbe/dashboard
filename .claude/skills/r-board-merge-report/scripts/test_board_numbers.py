#!/usr/bin/env python3
"""Tests for the numbers of the board merge report."""

import importlib.util
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


board_numbers = load("board_numbers", HERE / "board_numbers.py")

REQUIREMENTS = (
    "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
    '| <a id="r-1"></a>R-1 | One | in force | Keep the list short. See [R-2](#r-2). |\n'
    '| <a id="r-2"></a>R-2 | Two | in force | Keep the list short again. |\n'
    '| <a id="r-3"></a>R-3 | Three | planned | Work that is not finished. |\n'
)
ADR = (
    "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\nadrs: [R-2]\n---\n\n"
    "## Rule\n\nOne two three.\n"
)
HISTORY = (
    "---\nid: H-2026-11-22-slug\ntitle: Slug\nstatus: closed\n"
    "adrs: [R-2]\nroadmap: []\n---\n\n# Slug\n\n## Plan\n\nOne sentence here.\n"
)


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def sample(root):
    write(root, "docs/requirements/record.md", REQUIREMENTS)
    write(root, "docs/adr/ADR-0001.md", ADR)
    write(root, "docs/history/H-2026-11-22-slug.md", HISTORY)
    write(
        root,
        "tests/test_sample.py",
        'def test_one():\n    """id: R-1"""\n\n\ndef test_two():\n    """id: R-1"""\n',
    )
    write(root, "web/app.test.ts", "// id: R-2\n")
    write(root, "docs/ignored_test.py", '"""id: R-2"""\n')


def by_id(rows):
    return {row["id"]: row for row in rows}


class BoardNumbersTest(unittest.TestCase):
    def test_the_units_are_the_rows_the_adrs_and_the_history_files(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(
                sorted(rows),
                ["ADR-0001", "H-2026-11-22-slug", "R-1", "R-2"],
            )
            self.assertEqual(rows["R-1"]["kind"], "requirement")
            self.assertEqual(rows["R-2"]["status"], "in force")
            self.assertEqual(rows["ADR-0001"]["status"], "Accepted")
            self.assertEqual(rows["H-2026-11-22-slug"]["status"], "closed")

    def test_a_planned_row_is_out_of_scope(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            self.assertNotIn("R-3", by_id(board_numbers.numbers(root)))

    def test_a_list_with_no_status_column_is_in_force(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/requirements/record.md",
                "| Id | Title | Statement |\n| --- | --- | --- |\n"
                "| R-1 | One | Keep it short. |\n",
            )
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-1"]["status"], "in force")
            self.assertEqual(rows["R-1"]["words"], 4)
            self.assertIsNone(board_numbers.status_index(root / "docs" / "none.md"))

    def test_the_words_of_a_row_leave_out_the_id_the_anchor_and_the_link_target(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-1"]["words"], 7)
            self.assertEqual(rows["R-2"]["words"], 6)
            self.assertEqual(rows["ADR-0001"]["words"], 5)

    def test_a_test_counts_for_each_id_line_in_a_test_file_outside_docs(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-1"]["tests"], 2)
            self.assertEqual(rows["R-2"]["tests"], 1)

    def test_a_link_counts_only_when_it_comes_from_another_row_or_file(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-1"]["links"], 0)
            self.assertEqual(rows["R-2"]["links"], 1)

    def test_a_frontmatter_list_that_names_an_id_is_counted_apart(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-2"]["lists"], 2)
            self.assertEqual(rows["R-1"]["lists"], 0)

    def test_a_history_list_is_counted_and_a_history_link_is_not(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            write(
                root,
                "docs/history/H-2026-11-23-other.md",
                "---\nid: H-2026-11-23-other\nstatus: closed\n"
                "adrs: [R-2]\n---\n\nSee [R-2](../requirements/record.md#r-2).\n",
            )
            rows = by_id(board_numbers.numbers(root))
            self.assertEqual(rows["R-2"]["lists"], 3)
            self.assertEqual(rows["R-2"]["links"], 1)

    def test_rows_of_two_requirement_files_are_units_and_a_link_across_files_counts(
        self,
    ):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            write(
                root,
                "docs/requirements/plan.md",
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                "| R-4 | Four | in force | See [R-2](record.md#r-2). |\n"
                "| R-5 | Five | planned | Open. |\n",
            )
            rows = by_id(board_numbers.numbers(root))
            self.assertIn("R-4", rows)
            self.assertNotIn("R-5", rows)
            self.assertEqual(rows["R-2"]["links"], 2)

    def test_the_output_has_a_header_one_line_for_each_unit_and_a_total(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            text = board_numbers.render(board_numbers.numbers(root))
            lines = text.splitlines()
            self.assertEqual(
                lines[0], "board[4]{id,kind,status,words,tests,links,lists,names}:"
            )
            self.assertIn(
                "  R-1,requirement,in force,7,2,0,0,"
                "tests/test_sample.py::test_one;tests/test_sample.py::test_two",
                lines,
            )
            self.assertEqual(lines[-1], "total: 4 units, 25 words")

    def test_the_names_of_the_tests_of_an_id_are_printed_sorted_in_one_line(self):
        """id: R-86"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            write(
                root,
                "tests/test_other.py",
                'def test_zeta():\n    """id: R-1"""\n\n\n'
                "# id: R-1\ndef test_alpha():\n    pass\n",
            )
            write(
                root,
                "web/shape.test.ts",
                'it("keeps the list short", () => {\n  // id: R-2\n});\n',
            )
            write(
                root,
                "pkg/shape_test.go",
                "// id: R-2\nfunc TestShape(t *testing.T) {\n}\n",
            )
            text = board_numbers.render(board_numbers.numbers(root))
            line_one = next(x for x in text.splitlines() if x.startswith("  R-1,"))
            self.assertEqual(
                line_one.split(",")[-1],
                "tests/test_other.py::test_alpha;tests/test_other.py::test_zeta;"
                "tests/test_sample.py::test_one;tests/test_sample.py::test_two",
            )
            self.assertEqual(line_one.split(",")[4], "4")
            line_two = next(x for x in text.splitlines() if x.startswith("  R-2,"))
            self.assertIn("pkg/shape_test.go::TestShape", line_two)
            self.assertIn("web/shape.test.ts::keeps the list short", line_two)
            self.assertIn("web/app.test.ts", line_two.split(",")[-1].split(";"))

    def test_an_id_with_no_test_has_an_empty_names_cell(self):
        """id: R-86"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            text = board_numbers.render(board_numbers.numbers(root))
            self.assertIn("  ADR-0001,adr,Accepted,5,0,0,0,", text.splitlines())

    def test_a_named_id_narrows_the_rows_and_an_unknown_id_is_an_error(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            rows, errors = board_numbers.select(
                board_numbers.numbers(root), ["R-1", "R-9"]
            )
            self.assertEqual([row["id"] for row in rows], ["R-1"])
            self.assertEqual(errors, ["R-9 is not a unit in scope"])

    def test_the_main_function_fails_for_an_unknown_id(self):
        """id: R-77"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root)
            out, err = io.StringIO(), io.StringIO()
            here = Path.cwd()
            try:
                import os

                os.chdir(root)
                with redirect_stdout(out), redirect_stderr(err):
                    code = board_numbers.main(["board_numbers.py", "R-9"])
            finally:
                os.chdir(here)
            self.assertEqual(code, 1)
            self.assertIn("R-9", err.getvalue())

    def test_the_makefile_of_the_skill_defines_the_target_and_both_includes_name_it(
        self,
    ):
        """id: R-77"""
        mk = (ROOT / "skills/r-board-merge-report/merge-report.mk").read_text(
            encoding="utf-8"
        )
        self.assertRegex(mk, r"(?m)^board-numbers: ## \S")
        self.assertIn("scripts/board_numbers.py", mk)
        for name in ("r-project-setup/project.mk", "r-github-pipeline/sdlc.mk"):
            text = (ROOT / "skills" / name).read_text(encoding="utf-8")
            self.assertIn(
                "-include .claude/skills/r-board-merge-report/merge-report.mk", text
            )
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "include skills/r-board-merge-report/merge-report.mk", root_makefile
        )


class BoardMergeSkillsTest(unittest.TestCase):
    def targets(self):
        found = set()
        for path in (ROOT / "skills").glob("*/*.mk"):
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^([a-z][a-z0-9-]*):", line)
                if match:
                    found.add(match.group(1))
        return found

    def test_each_make_target_that_the_two_skills_name_exists(self):
        """id: R-78"""
        defined = self.targets()
        for name in ("r-board-merge-report", "r-board-merge"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            named = set(re.findall(r"`make ([a-z][a-z0-9-]*)", text))
            self.assertIn("board-numbers", named, name)
            self.assertEqual(named - defined, set(), name)


if __name__ == "__main__":
    unittest.main()
