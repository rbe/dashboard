#!/usr/bin/env python3
"""The report, the requirement id, and test-changed."""

import importlib.util
import io
import json
import os
import re
import subprocess
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


requirements = load("requirements", HERE / "requirements.py")
select_tests = load("select_tests", HERE / "select_tests.py")
project_report = load("project_report", HERE / "project_report.py")
changed_tests = load("changed_tests", HERE / "changed_tests.py")
node_cover_map = load("node_cover_map", HERE / "node_cover_map.py")
jacoco_cover_map = load("jacoco_cover_map", HERE / "jacoco_cover_map.py")
go_cover_map = load("go_cover_map", HERE / "go_cover_map.py")


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class RequirementIdTest(unittest.TestCase):
    def test_a_missing_id_fails_the_check(self):
        """id: R-1"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "tests/test_sample.py",
                "def test_runs():\n    assert True\n",
            )
            errors = requirements.problems(
                requirements.collect(root), requirements.proofs(root)
            )
            self.assertTrue(any("has no id" in error for error in errors))

    def test_a_path_does_not_name_the_requirement(self):
        """id: R-1"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "tests/test_sample.py",
                'def test_runs():\n    """See docs/adr/ADR-0001.md"""\n    assert True\n',
            )
            errors = requirements.problems(
                requirements.collect(root), requirements.proofs(root)
            )
            self.assertTrue(any("has no id" in error for error in errors))

    def test_an_id_that_is_not_a_requirement_fails(self):
        """id: R-1"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "tests/test_sample.py",
                'def test_runs():\n    """id: ADR-9999"""\n    assert True\n',
            )
            errors = requirements.problems(
                requirements.collect(root), requirements.proofs(root)
            )
            self.assertTrue(any("not a requirement" in error for error in errors))

    def test_review_fails_a_test_that_has_no_id(self):
        """id: R-1"""
        for text in general_rules():
            self.assertIn("Stop when a test has no id.", text)
        record = (ROOT / "skills" / "record" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`id:`", record)
        self.assertIn("does not build a path", record)

    def test_a_test_in_another_language_names_its_id_in_a_comment(self):
        """id: R-63"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "src/a.test.ts",
                "// id: ADR-0001\n// id: ADR-0001\ntest('a', () => {})\n",
            )
            write(
                root,
                "src/test/java/PortTest.java",
                "/**\n * id: ADR-0001\n */\nclass PortTest {}\n",
            )
            write(root, "src/b.spec.js", "test('b', () => {})\n")
            found = requirements.proofs(root)
            named = {proof.path: proof.requirement_id for proof in found}
            self.assertEqual(named["src/a.test.ts"], "ADR-0001")
            self.assertEqual(named["src/test/java/PortTest.java"], "ADR-0001")
            self.assertIsNone(named["src/b.spec.js"])
            errors = requirements.problems(requirements.collect(root), found)
            self.assertEqual(errors, ["src/b.spec.js has no id"])
            text, _errors = project_report.build(root)
            self.assertEqual(text.count("src/a.test.ts; src/a.test.ts"), 0)

    def test_a_test_inside_an_installed_skill_is_not_a_project_test(self):
        """id: R-63"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                ".claude/skills/record/scripts/test_record.py",
                'def test_runs():\n    """id: R-13"""\n    assert True\n',
            )
            write(root, "node_modules/x/x.test.js", "test('x', () => {})\n")
            write(
                root,
                "apm_modules/rbe/ralfskills/skills/record/scripts/test_record.py",
                'def test_runs():\n    """id: R-13"""\n    assert True\n',
            )
            self.assertEqual(requirements.proofs(root), [])

    def test_every_test_in_this_repository_names_a_requirement(self):
        """id: R-1"""
        errors = requirements.problems(
            requirements.collect(ROOT), requirements.proofs(ROOT)
        )
        self.assertEqual(errors, [])


class ChangedTestsTest(unittest.TestCase):
    def test_coverage_of_a_file_selects_its_tests(self):
        """id: R-2"""
        covered = select_tests.merge_covered(
            {"pkg.Test.test_one": ["pkg/app.py"]},
            {
                "pkg.Test.test_one": ["docs/ROADMAP.md"],
                "pkg.Test.test_two": ["docs/ROADMAP.md"],
                "": ["pkg/ignored.py"],
            },
        )
        self.assertEqual(
            select_tests.select(["pkg/app.py"], covered), ["pkg.Test.test_one"]
        )
        self.assertEqual(
            select_tests.select(["docs/ROADMAP.md"], covered),
            ["pkg.Test.test_one", "pkg.Test.test_two"],
        )
        self.assertNotIn("", covered)
        script = (HERE / "changed_tests.py").read_text(encoding="utf-8")
        self.assertIn("covered.json", script)
        self.assertNotIn("SKILL.md", script)

    def test_a_missing_coverage_map_stops_test_changed(self):
        """id: R-2"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            error = io.StringIO()
            with redirect_stderr(error):
                code = changed_tests.run(root)
            self.assertEqual(code, 1)
            self.assertIn("make coverage", error.getvalue())

    def test_no_covering_test_still_names_the_full_suite(self):
        """id: R-2"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coverage = root / "build" / "coverage"
            coverage.mkdir(parents=True)
            (coverage / "changed.txt").write_text("README.md\n", encoding="utf-8")
            (coverage / "covered.json").write_text("{}\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = changed_tests.run(root)
            self.assertEqual(code, 0)
            self.assertIn("make test runs the full suite", output.getvalue())

    def test_a_node_test_file_covers_the_files_that_ran_in_its_process(self):
        """id: R-2"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            v8 = root / "build" / "coverage" / "v8"

            def script(relative, count):
                ranges = [{"startOffset": 0, "endOffset": 9, "count": count}]
                return {
                    "url": f"file://{root.as_posix()}/{relative}",
                    "functions": [{"functionName": "", "ranges": ranges}],
                }

            first = [
                script("test/a.test.js", 1),
                script("src/a.js", 1),
                script("src/unused.js", 0),
                script("node_modules/x/index.js", 1),
                {"url": "node:internal/main", "functions": []},
            ]
            second = [script("test/b.test.js", 1), script("src/b.js", 1)]
            runner = [script("src/a.js", 1)]
            for name, result in (("1", first), ("2", second), ("3", runner)):
                write(
                    root,
                    f"build/coverage/v8/coverage-{name}.json",
                    json.dumps({"result": result}),
                )
            found = node_cover_map.covered(v8, root)
            self.assertEqual(
                found,
                {
                    "test/a.test.js": {"test/a.test.js", "src/a.js"},
                    "test/b.test.js": {"test/b.test.js", "src/b.js"},
                },
            )

    def test_an_empty_node_map_fails_and_names_the_reason(self):
        """id: R-2"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "build/coverage/v8/coverage-1.json", json.dumps({"result": []}))
            previous = Path.cwd()
            errors = io.StringIO()
            try:
                os.chdir(root)
                with redirect_stderr(errors):
                    code = node_cover_map.main(["node_cover_map.py"])
            finally:
                os.chdir(previous)
            self.assertEqual(code, 1)
            self.assertIn("no test file ran under V8 coverage", errors.getvalue())
            self.assertFalse((root / "build/coverage/covered.json").exists())

    def test_a_jvm_test_class_covers_the_classes_that_ran_in_its_jvm(self):
        """id: R-2"""

        def text(value):
            data = value.encode("utf-8")
            return len(data).to_bytes(2, "big") + data

        def session(name, classes):
            block = b"\x01\xc0\xc0\x10\x07"
            block += b"\x10" + text(name) + bytes(16)
            for class_name, hit in classes:
                probes = b"\x05" if hit else b"\x00"
                block += b"\x11" + bytes(8) + text(class_name) + b"\x03" + probes
            return block

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("A", "B"):
                write(root, f"src/main/java/com/x/{name}.java", "class X {}\n")
                write(root, f"src/test/java/com/x/{name}Test.java", "class X {}\n")
            data = session(
                "one",
                [("com/x/ATest", True), ("com/x/A$Inner", True), ("com/x/B", False)],
            )
            data += session("two", [("com/x/BTest", True), ("com/x/B", True)])
            write(root, "build/jacoco/test.exec", "")
            (root / "build" / "jacoco" / "test.exec").write_bytes(data)
            found = jacoco_cover_map.covered([root / "build/jacoco/test.exec"], root)
            self.assertEqual(
                found,
                {
                    "com.x.ATest": {
                        "src/main/java/com/x/A.java",
                        "src/test/java/com/x/ATest.java",
                    },
                    "com.x.BTest": {
                        "src/main/java/com/x/B.java",
                        "src/test/java/com/x/BTest.java",
                    },
                },
            )

    def test_a_go_package_covers_the_files_its_tests_ran(self):
        """id: R-68"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "go.mod", "module example.com/app\n\ngo 1.22\n")
            write(root, "internal/fmt/fmt.go", "package fmt\n")
            write(root, "internal/fmt/fmt_test.go", "// id: D-1\npackage fmt\n")
            write(root, "internal/ui/ui.go", "package ui\n")
            write(root, "internal/ui/ui_test.go", "// id: D-1\npackage ui\n")
            write(root, "main_test.go", "// id: D-1\npackage main\n")
            write(root, "build/coverage/go/example.com_app.out", "mode: set\n")
            write(
                root,
                "build/coverage/go/example.com_app_internal_fmt.out",
                "mode: set\n"
                "example.com/app/internal/fmt/fmt.go:3.20,5.2 1 1\n"
                "example.com/app/internal/fmt/fmt.go:7.20,9.2 1 0\n"
                "example.com/app/internal/ui/ui.go:3.20,4.2 1 0\n",
            )
            write(
                root,
                "build/coverage/go/example.com_app_internal_ui.out",
                "mode: set\n"
                "example.com/app/internal/fmt/fmt.go:3.20,5.2 1 1\n"
                "example.com/app/internal/ui/ui.go:3.20,4.2 1 1\n"
                "other.org/lib/x.go:1.1,2.2 1 1\n",
            )
            by_test, lines = go_cover_map.covered(root / "build/coverage/go", root)
            self.assertEqual(
                by_test,
                {
                    ".": {"main_test.go"},
                    "./internal/fmt": {
                        "internal/fmt/fmt.go",
                        "internal/fmt/fmt_test.go",
                    },
                    "./internal/ui": {
                        "internal/fmt/fmt.go",
                        "internal/ui/ui.go",
                        "internal/ui/ui_test.go",
                    },
                },
            )
            self.assertEqual(lines["internal/fmt/fmt.go"][4], 1)
            self.assertEqual(lines["internal/fmt/fmt.go"][8], 0)
            self.assertNotIn("x.go", "".join(lines))
            xml = go_cover_map.cobertura(lines)
            self.assertIn('filename="internal/fmt/fmt.go"', xml)
            self.assertIn('<line number="8" hits="0"/>', xml)
            previous = Path.cwd()
            try:
                os.chdir(root)
                self.assertEqual(go_cover_map.main(["go_cover_map.py"]), 0)
                errors = io.StringIO()
                with redirect_stderr(errors):
                    self.assertEqual(go_cover_map.main(["go_cover_map.py"]), 1)
            finally:
                os.chdir(previous)
            self.assertIn("no Go cover profile", errors.getvalue())
            self.assertTrue((root / "build/coverage/coverage.xml").is_file())

    def test_a_go_test_file_names_its_id_in_a_comment(self):
        """id: R-63"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "internal/fmt/fmt_test.go", "// id: D-1\npackage fmt\n")
            write(root, "internal/ui/ui_test.go", "package ui\n")
            named = {
                proof.path: proof.requirement_id for proof in requirements.proofs(root)
            }
            self.assertEqual(named["internal/fmt/fmt_test.go"], "D-1")
            self.assertIsNone(named["internal/ui/ui_test.go"])

    def test_the_print_mode_names_the_chosen_tests_and_runs_none(self):
        """id: R-2"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "build/coverage/covered.json",
                json.dumps(
                    {"test/a.test.js": ["src/a.js"], "test/b.test.js": ["src/b.js"]}
                ),
            )
            write(root, "build/coverage/changed.txt", "src/b.js\n")
            output = io.StringIO()
            with redirect_stdout(output):
                code = changed_tests.run(root, only_print=True)
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), "test/b.test.js\n")

    def test_ci_runs_the_full_suite(self):
        """id: R-2"""
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("TEST_CHANGED_CMD", makefile)
        self.assertIn("cover_tests.py", makefile)
        self.assertIn("$(PYTHON) -m unittest $(UNIT_TESTS)", makefile)
        setup = ROOT / "skills" / "project-setup"
        fragment = (setup / "test-changed.mk").read_text(encoding="utf-8")
        self.assertIn("test-changed:", fragment)
        project = (setup / "project.mk").read_text(encoding="utf-8")
        self.assertIn("include $(PROJECT_MK_DIR)test-changed.mk", project)
        sdlc = (ROOT / "skills" / "github-pipeline" / "sdlc.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("project-setup/test-changed.mk", sdlc)
        ci_targets = [line for line in sdlc.splitlines() if line.startswith("SDLC_CI")]
        self.assertEqual(len(ci_targets), 1)
        self.assertNotIn("test-changed", ci_targets[0])
        develop = (ROOT / "skills" / "develop" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("A green `test-changed` does not replace `make test`.", develop)
        for name in ("ci.node.yml", "ci.gradle.yml"):
            workflow = (
                ROOT / "skills" / "github-pipeline" / "templates" / name
            ).read_text(encoding="utf-8")
            self.assertIn("\n      - run: make test\n", workflow)
            self.assertNotIn("test-changed", workflow)


ENTRY_FILES = ("CLAUDE.md", "skills/project-setup/templates/CLAUDE.md")


def general_rules():
    """The general rules of the entry file and of its template.

    A skill does not repeat a general rule, so a test reads the rule here.
    """
    found = []
    for name in ENTRY_FILES:
        text = (ROOT / name).read_text(encoding="utf-8")
        found.append(text.split("<general_rules>", 1)[1].split("</general_rules>")[0])
    return found


class RequirementFilesTest(unittest.TestCase):
    def files(self):
        return sorted((ROOT / "docs" / "requirements").glob("*.md"))

    def test_there_is_no_single_requirements_file_and_one_file_for_each_owner(self):
        """id: R-28"""
        self.assertFalse((ROOT / "docs" / "REQUIREMENTS.md").exists())
        skills = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
        for path in self.files():
            self.assertIn(path.stem, skills | {"collection"}, path.name)

    def test_each_row_stands_once_with_the_columns_of_the_table_form(self):
        """id: R-28"""
        seen = []
        for path in self.files():
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertIn("| Id | Title | Status | Statement |", lines, path.name)
            for row in requirements.table_rows(path):
                self.assertIn(row["status"], ("in force", "planned"), row["id"])
                seen.append(row["id"])
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)))

    def test_the_report_of_this_collection_links_each_row_to_its_own_file(self):
        """id: R-28"""
        text, _errors = project_report.build(ROOT)
        self.assertIn("(../docs/requirements/record.md#r-13)", text)
        self.assertIn("(../docs/requirements/project-setup.md#r-45)", text)
        self.assertNotIn("REQUIREMENTS.md", text)


class GeneralRulesTest(unittest.TestCase):
    def test_the_entry_file_and_its_template_have_the_same_general_rules(self):
        """id: R-76"""
        for name in ENTRY_FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("\n## General rules\n"), 1)
            self.assertEqual(text.count("<general_rules>"), 1)
            self.assertEqual(text.count("</general_rules>"), 1)
            self.assertLess(
                text.index("</general_rules>"),
                text.index("\n## Communication contract\n"),
            )
        collection, template = general_rules()
        self.assertEqual(collection, template)

    def test_the_entry_file_and_its_template_stay_within_their_word_limits(self):
        """id: R-76"""
        limits = {"CLAUDE.md": 845, "skills/project-setup/templates/CLAUDE.md": 915}
        for name, limit in limits.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertLessEqual(len(text.split()), limit, name)

    def test_the_entry_file_and_its_template_hold_the_group_questions(self):
        """id: R-51"""
        for name in ENTRY_FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            contract = text[text.index("\n## Communication contract\n") :]
            self.assertEqual(contract.count("\nQuestions:\n"), 1, name)
            self.assertLess(
                contract.index("\nContent:\n"), contract.index("\nQuestions:\n")
            )
            self.assertLess(
                contract.index("\nQuestions:\n"), contract.index("\nExample.")
            )
            self.assertIn("Never write a bare id.", contract, name)
            self.assertIn("as a Markdown link to its definition", contract, name)
            self.assertIn("Recommend one choice.", contract, name)

    def test_the_general_rules_name_the_interface_and_the_start_of_a_task(self):
        """id: R-75"""
        for text in general_rules():
            self.assertIn("Type only `make <target>` and Git commands.", text)
            self.assertIn("The host needs only Make, Git, and Podman.", text)
            self.assertIn(
                "A typed tool of POSIX `sh`, such as `tail` or `grep`, "
                "may only shorten or search output, and writes no file.",
                text,
            )
            self.assertIn("Run `make old-board` before the first skill.", text)
            self.assertIn("the only skill is `migrate-docs`", text)
            self.assertIn("`record` writes every id and every board document.", text)
            self.assertIn("Run `make toon` before you read an index.", text)

    def test_a_requirements_repository_reads_the_requirements_index(self):
        """id: R-54"""
        for text in general_rules():
            self.assertIn(
                "Where a step names `docs/adr/index.toon`, read "
                "`docs/requirements-index.toon` in such a repository",
                text,
            )
        for name in ("develop", "review"):
            skill = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`docs/adr/index.toon`", skill)
            self.assertNotIn("skip this step", skill)
            self.assertNotIn("If the repository keeps `docs/adr/`", skill)


ONE_LINE = "The general rules in `CLAUDE.md` apply."
SKILL_TAGS = (
    "purpose",
    "inputs",
    "steps",
    "rules",
    "output",
    "references",
    "example",
    "questions",
    "checks",
)
OLD_BOARD = (
    "docs/BUGS.md",
    "docs/WAVES.md",
    "docs/FEATURES.md",
    "docs/DECISIONS.md",
    "docs/KNOWN_ISSUES.md",
    "docs/bugs/",
    "docs/waves/",
    "docs/features/",
)


def skill_files():
    return sorted((ROOT / "skills").glob("*/SKILL.md"))


def skill_body(path):
    """The lines of a skill file after its frontmatter."""
    text = path.read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[1].splitlines()


def tag_problems(lines):
    """Each line that breaks the tag shape of a skill file.

    A tag line is a line that holds one tag and no other text.
    """
    problems = []
    open_tags = []
    for line in lines:
        closing = re.fullmatch(r"</([a-z]+)>", line)
        opening = re.fullmatch(r'<([a-z]+)(?: name="[a-z-]+")?>', line)
        if closing:
            if not open_tags or open_tags.pop() != closing.group(1):
                problems.append(line)
        elif opening:
            name = opening.group(1)
            inside_mode = open_tags == ["mode"] and name in ("steps", "rules")
            known = name in SKILL_TAGS or name == "mode"
            if not known or (open_tags and not inside_mode):
                problems.append(line)
            open_tags.append(name)
        elif line.startswith("#"):
            problems.append(line)
    return problems + [f"<{name}> is not closed" for name in open_tags]


class SkillShapeTest(unittest.TestCase):
    def test_each_skill_refers_to_the_general_rules_in_one_line(self):
        """id: R-76"""
        self.assertEqual(len(skill_files()), 22)
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(ONE_LINE), 1, path)
            self.assertEqual(skill_body(path)[:3], ["", ONE_LINE, ""], path)

    def test_each_skill_body_is_closed_tags_of_the_fixed_vocabulary(self):
        """id: R-76"""
        for path in skill_files():
            self.assertEqual(tag_problems(skill_body(path)), [], path)

    def test_the_tag_check_finds_a_heading_an_unknown_tag_and_an_open_tag(self):
        """id: R-76"""
        self.assertEqual(tag_problems(["<steps>", "1. One.", "</steps>"]), [])
        self.assertEqual(
            tag_problems(['<mode name="setup">', "<rules>", "</rules>", "</mode>"]),
            [],
        )
        self.assertEqual(tag_problems(["## Work"]), ["## Work"])
        self.assertEqual(tag_problems(["<notes>", "</notes>"]), ["<notes>"])
        self.assertEqual(
            tag_problems(["<steps>", "<rules>", "</rules>", "</steps>"]), ["<rules>"]
        )
        self.assertEqual(tag_problems(["<steps>"]), ["<steps> is not closed"])

    def test_only_migrate_docs_names_a_path_of_the_old_board(self):
        """id: R-21"""
        for path in skill_files():
            if path.parent.name == "migrate-docs":
                continue
            text = path.read_text(encoding="utf-8")
            for old_path in OLD_BOARD:
                self.assertNotIn(old_path, text, path)

    def test_a_skill_names_each_of_its_reference_files(self):
        """id: R-76"""
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            named = set(re.findall(r"`references/([a-z-]+\.md)`", text))
            kept = {item.name for item in (path.parent / "references").glob("*.md")}
            self.assertEqual(named, kept, path)


class ProjectReportTest(unittest.TestCase):
    def sample(self, root):
        write(
            root,
            "docs/adr/ADR-0001.md",
            "---\nid: ADR-0001\ntitle: Listen on localhost\nstatus: Accepted\n---\n\n# Listen\n",
        )
        write(
            root,
            "docs/requirements/core.md",
            "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
            "| R-1 | Keep the host make | in force | The host runs make only. |\n"
            "| R-2 | Name the port | planned | Which port. |\n",
        )
        write(
            root,
            "docs/ROADMAP.md",
            "| Id | Kind | Title | Proposal |\n| --- | --- | --- | --- |\n"
            "| W-1 | feature | Add a port. | |\n",
        )
        write(
            root,
            "skills/plan/SKILL.md",
            "---\nname: plan\n---\n\n<steps>\n1. Name who owns state.\n</steps>\n",
        )
        write(
            root,
            "skills/develop/SKILL.md",
            "---\nname: develop\n---\n\n<purpose>\n1. Not a step.\n</purpose>\n"
            "<steps>\n1. Run `make lint` and `make test`.\n</steps>\n"
            "<rules>\n1. Not a step either.\n</rules>\n",
        )
        write(
            root,
            "tests/test_sample.py",
            'def test_listens_on_localhost():\n    """id: ADR-0001"""\n    assert True\n',
        )

    def test_the_report_names_the_tests_and_the_gaps(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            text, errors = project_report.build(root)
            self.assertEqual(errors, [])
            self.assertIn(
                "| [ADR-0001](../docs/adr/ADR-0001.md) | adr | Accepted | tests.test_sample.test_listens_on_localhost |",
                text,
            )
            gap = text.split("### Ids with no test", 1)[1].split(
                "### Tests with no id", 1
            )[0]
            self.assertIn("[R-1](../docs/requirements/core.md#r-1) (requirement)", gap)
            self.assertNotIn("R-2", gap)
            self.assertNotIn("W-1", gap)
            roadmap = text.split("### Roadmap", 1)[1].split("### Checks", 1)[0]
            self.assertIn(
                "[W-1](../docs/ROADMAP.md#w-1), feature, roadmap. Add a port.", roadmap
            )
            self.assertIn(
                "[R-2](../docs/requirements/core.md#r-2), planned. Name the port.", text
            )
            self.assertNotIn("ADR-0001](../docs/adr/ADR-0001.md) (adr)", gap)
            self.assertIn("Hand-editing this file is a defect.", text)

    def test_a_requirement_row_beside_the_adrs_is_a_requirement_a_test_can_name(self):
        """id: R-67"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                "| R-2 | Divide | in force | divide raises on zero. |\n",
            )
            write(
                root,
                "tests/test_core.py",
                'def test_divide_raises_on_zero():\n    """id: R-2"""\n    assert True\n',
            )
            text, errors = project_report.build(root)
            self.assertEqual(errors, [])
            self.assertIn(
                "| [R-2](../docs/requirements/core.md#r-2) | requirement | in force | tests.test_core.test_divide_raises_on_zero |",
                text,
            )

    def test_a_test_does_not_name_a_roadmap_row_or_a_planned_row(self):
        """id: R-1"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "docs/ROADMAP.md",
                "| Id | Kind | Title | Proposal |\n| --- | --- | --- | --- |\n"
                "| W-1 | defect | divide returns 0 on zero. | |\n",
            )
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                "| R-5 | Divide | planned | divide must raise. |\n",
            )
            write(
                root,
                "tests/test_core.py",
                'def test_one():\n    """id: W-1"""\n    assert True\n\n\n'
                'def test_two():\n    """id: R-5"""\n    assert True\n',
            )
            text, errors = project_report.build(root)
            self.assertEqual(len(errors), 2)
            self.assertIn("names W-1, which is not a requirement", errors[0])
            self.assertIn("names R-5, which is not a requirement", errors[1])
            proof_map = text.split("## Architecture review", 1)[0]
            self.assertNotIn("| W-1 |", proof_map)
            self.assertNotIn("| R-5 |", proof_map)
            self.assertIn(
                "[W-1](../docs/ROADMAP.md#w-1), defect, roadmap. divide returns 0 on zero.",
                text,
            )
            self.assertNotIn("zero.. Proved", text)

    def test_a_superseded_adr_is_not_an_id_with_no_test(self):
        """id: R-56"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            write(
                root,
                "docs/adr/ADR-0002.md",
                "---\nid: ADR-0002\ntitle: Listen on a socket\nstatus: Superseded\n---\n",
            )
            write(
                root,
                "docs/adr/ADR-0003.md",
                "---\nid: ADR-0003\ntitle: Listen on a port\nstatus: Accepted\n"
                "supersedes: [ADR-0002]\n---\n",
            )
            text, errors = project_report.build(root)
            self.assertEqual(errors, [])
            gap = text.split("### Ids with no test", 1)[1].split(
                "### Tests with no id", 1
            )[0]
            self.assertNotIn("ADR-0002](../docs/adr/ADR-0002.md) (adr)", gap)
            self.assertIn("[ADR-0003](../docs/adr/ADR-0003.md) (adr)", gap)
            self.assertIn(
                "| [ADR-0002](../docs/adr/ADR-0002.md) | adr | Superseded | no test |",
                text,
            )

    def test_a_requirements_list_is_the_map_when_there_is_no_adr_file(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Statement |\n| --- | --- |\n| R-1 | A test names the requirement. |\n",
            )
            write(
                root,
                "tests/test_sample.py",
                'def test_names_it():\n    """id: R-1"""\n    assert True\n',
            )
            text, errors = project_report.build(root)
            self.assertEqual(errors, [])
            self.assertIn(
                "| [R-1](../docs/requirements/core.md#r-1) | requirement |", text
            )
            self.assertIn("The id is a row in a file in `docs/requirements/`.", text)
            self.assertNotIn("### ADRs", text)

    def test_an_adr_file_keeps_the_product_report_and_reads_the_requirement_rows(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Title | Statement |\n| --- | --- | --- |\n| R-9 | Other | Other. |\n",
            )
            text, errors = project_report.build(root)
            self.assertEqual(errors, [])
            self.assertIn(
                "| [ADR-0001](../docs/adr/ADR-0001.md) | adr | Accepted |", text
            )
            self.assertIn("### ADRs", text)
            self.assertIn(
                "| [R-9](../docs/requirements/core.md#r-9) | requirement | in force |",
                text,
            )

    def test_the_reviews_quote_the_stage_checks(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            text, _errors = project_report.build(root)
            architecture = text.split("## Architecture review", 1)[1].split(
                "## Development review", 1
            )[0]
            development = text.split("## Development review", 1)[1]
            self.assertIn("Listen on localhost", architecture)
            self.assertIn("Name who owns state.", architecture)
            self.assertIn("review: not installed", architecture)
            self.assertIn("Add a port.", development)
            self.assertIn("Name the port", development)
            self.assertIn("Run `make lint` and `make test`.", development)
            self.assertIn("project-setup: not installed", development)

    def test_the_reviews_read_the_checks_tag_of_project_setup(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            write(
                root,
                "skills/project-setup/SKILL.md",
                '---\nname: project-setup\n---\n\n<mode name="setup">\n<steps>\n'
                "1. Ask how the project ships.\n</steps>\n</mode>\n\n<checks>\n"
                "1. `integration` is the one integration entry.\n"
                "   Stop when a second one exists.\n"
                "2. `lint` is one linter.\n</checks>\n",
            )
            text, _errors = project_report.build(root)
            development = text.split("## Development review", 1)[1]
            self.assertIn(
                "- 1. `integration` is the one integration entry. "
                "Stop when a second one exists.\n- 2. `lint` is one linter.\n",
                development,
            )
            self.assertNotIn("Ask how the project ships.", development)
            self.assertNotIn("Not a step", development)

    def test_the_reviews_still_read_a_skill_that_keeps_the_work_heading(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            write(
                root,
                "skills/review/SKILL.md",
                "# Review\n\n## Steps\n\n1. Not a check.\n\n## Work\n\n"
                "1. Run the gates.\n\n## Later\n\n1. Not a check.\n",
            )
            text, _errors = project_report.build(root)
            self.assertEqual(text.count("- 1. Run the gates."), 2)
            self.assertNotIn("Not a check.", text)

    def test_make_project_report_is_the_writer(self):
        """id: R-3"""
        for name in ("review", "project-setup", "project-report"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`make project-report`", text)
        report = (ROOT / "skills" / "project-report" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`make project-report` writes `build/project-report.md`", report)
        for text in general_rules():
            self.assertIn(
                "Hand-editing a file that a Make target writes is a defect.", text
            )
        contract = (ROOT / "skills" / "project-setup" / "contract.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("project-report:", contract)

    def test_this_repository_report_maps_the_requirements_list(self):
        """id: R-3"""
        text, errors = project_report.build(ROOT)
        self.assertEqual(errors, [])
        self.assertIn("## Requirements", text)
        self.assertIn("## Architecture review", text)
        self.assertIn("## Development review", text)
        self.assertIn("| [R-7](../docs/requirements/plan.md#r-7) | requirement |", text)
        gap = text.split("### Ids with no test", 1)[1].split("### Tests with no id", 1)[
            0
        ]
        self.assertNotIn("(roadmap)", gap)
        architecture = text.split("## Architecture review", 1)[1].split(
            "## Development review", 1
        )[0]
        development = text.split("## Development review", 1)[1]
        self.assertIn("who owns state", architecture)
        self.assertIn("one integration entry", development)
        self.assertIn("### Planned requirements", development)
        self.assertNotIn("[R-85](", development)
        self.assertNotIn("### Decisions", development)


class ReportLinkTest(unittest.TestCase):
    def test_the_map_links_an_adr_and_a_requirement_row(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Title | Status | Statement |\n| --- | --- | --- | --- |\n"
                '| <a id="r-2"></a>R-2 | See ADR-0001 and `R-2`. | planned | One. |\n',
            )
            text, _errors = project_report.build(root)
            self.assertIn("| [ADR-0001](../docs/adr/ADR-0001.md) | adr |", text)
            self.assertIn(
                "[R-2](../docs/requirements/core.md#r-2), planned. See [ADR-0001](../docs/adr/ADR-0001.md) and `R-2`.",
                text,
            )
            (root / "docs" / "adr" / "ADR-0001.md").unlink()
            write(
                root,
                "docs/requirements/core.md",
                "| Id | Title | Statement |\n| --- | --- | --- |\n"
                '| <a id="r-12"></a>R-12 | One. | Two. |\n',
            )
            text, _errors = project_report.build(root)
            self.assertIn(
                "| [R-12](../docs/requirements/core.md#r-12) | requirement |", text
            )
            self.assertIn("- [R-12](../docs/requirements/core.md#r-12). One.", text)

    def test_a_roadmap_row_links_to_its_row(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/adr/ADR-0001.md",
                "---\nid: ADR-0001\ntitle: One\nstatus: Accepted\n---\n",
            )
            write(
                root,
                "docs/ROADMAP.md",
                "| Id | Kind | Title | Proposal |\n| --- | --- | --- | --- |\n"
                '| <a id="w-3"></a>W-3 | feature | Divide. | |\n',
            )
            text, _errors = project_report.build(root)
            self.assertIn("[W-3](../docs/ROADMAP.md#w-3), feature, roadmap.", text)

    def test_an_anchored_id_cell_is_read_as_the_bare_id(self):
        """id: R-69"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "docs/ROADMAP.md",
                "| Id | Kind | Title | Proposal |\n| --- | --- | --- | --- |\n"
                '| <a id="w-5"></a>W-5 | question | Later. | |\n',
            )
            rows = requirements.roadmap_rows(root)
            self.assertEqual([row.id for row in rows], ["W-5"])
            self.assertEqual(rows[0].status, "question")
            self.assertEqual(requirements.strip_anchor('<a id="w-5"></a>W-5'), "W-5")


HOST_TOOL = re.compile(
    r"(?:^|[\s;|&(])"
    r"(gh|jq|brew|curl|apm|pip|pip3|npm|npx|node|python|python3|gradle|go)"
    r" +[a-z-]"
)


PODMAN_VARIABLES = "GO_RUN|GO|NODE_RUN|NODE|GRADLE_RUN|GRADLE|PYTHON|GH|APM"


def recipe_lines(path):
    """The lines of a makefile that are not comments."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if not line.lstrip().startswith("#")]


def host_calls(path):
    """Recipe lines that call a tool the host does not have.

    The rest of a command that starts with `podman run` or with a
    Podman variable, as in `$(GO_RUN) go build`, runs in the container.
    So does a tool inside quotes, as in `sh -c '...'`. A `## ` help text
    is not a call. GO_FILES is a fragment of a `$(GO_RUN) sh -c` command.
    """
    found = []
    for line in recipe_lines(path):
        if line.startswith("GO_FILES = "):
            continue
        outside = line.split(" ## ")[0]
        outside = re.sub(r"'[^']*'", "''", outside)
        outside = re.sub(r'"[^"]*"', '""', outside)
        outside = re.sub(
            rf"(podman run|\$\(({PODMAN_VARIABLES})\))[^;|&]*", " ", outside
        )
        if HOST_TOOL.search(outside):
            found.append(f"{path.name}: {line.strip()}")
    return found


class MakeAndPodmanInterfaceTest(unittest.TestCase):
    SETUP = ROOT / "skills" / "project-setup"
    PIPELINE = ROOT / "skills" / "github-pipeline"

    def makefiles(self):
        files = sorted((ROOT / "skills").glob("*/*.mk"))
        files += sorted((ROOT / "skills").glob("*/templates/Makefile.*"))
        files.append(ROOT / "Makefile")
        return files

    def test_no_recipe_calls_a_host_tool_other_than_git_and_podman(self):
        """id: R-75"""
        self.assertGreater(len(self.makefiles()), 15)
        found = []
        for path in self.makefiles():
            found += host_calls(path)
        self.assertEqual(found, [])

    def test_the_host_call_check_finds_a_host_tool(self):
        """id: R-75"""
        with tempfile.TemporaryDirectory() as tmp:
            bad = write(
                Path(tmp),
                "bad.mk",
                "a:\n\tgh api repos/x\n\tif curl -fsS http://x; then true; fi\n"
                "\tx=$$(jq -r .a f.json)\n\tbrew install jq\n",
            )
            good = write(
                Path(tmp),
                "good.mk",
                "# gh api is a comment\na: ## Run go in Podman\n\t$(GH) api repos/x\n"
                "\t$(GO_RUN) sh -c 'go test ./...'\n\t$(NODE) npm ci\n"
                "\tpodman run --rm $(GO_IMAGE) go run .\n\tgit log\n",
            )
            self.assertEqual(len(host_calls(bad)), 4)
            self.assertEqual(host_calls(good), [])

    def test_doctor_checks_only_make_git_and_podman(self):
        """id: R-73"""
        doctor = "\n".join(recipe_lines(self.SETUP / "doctor.mk"))
        for tool in ("$(MAKE) --version", "git --version", "podman info"):
            self.assertIn(tool, doctor)
        self.assertIn("git remote get-url origin", doctor)
        self.assertEqual(re.findall(r"command -v (\w+)", doctor), ["podman"])
        for name in ("doctor.mk", "contract.mk", "tools.mk", "project.mk"):
            text = (self.SETUP / name).read_text(encoding="utf-8")
            self.assertNotIn("brew", text.lower())
        doctor_mk = (self.SETUP / "doctor.mk").read_text(encoding="utf-8")
        self.assertIn("\nsetup: doctor\n", doctor_mk)
        index_mk = (ROOT / "skills/record/index.mk").read_text(encoding="utf-8")
        self.assertIn("ifdef DOCTOR_MK\ntoon: doctor\nendif", index_mk)
        for name in ("project.mk", "../github-pipeline/sdlc.mk"):
            text = (self.SETUP / name).read_text(encoding="utf-8")
            self.assertLess(text.index("doctor.mk"), text.index("contract.mk"), name)
            self.assertLess(
                text.index("doctor.mk"), text.index("record/index.mk"), name
            )

    def test_the_podman_machine_starts_behind_a_target(self):
        """id: R-75"""
        doctor_mk = (self.SETUP / "doctor.mk").read_text(encoding="utf-8")
        recipe = "\n".join(recipe_lines(self.SETUP / "doctor.mk"))
        self.assertIn("\npodman-start: ##", doctor_mk)
        self.assertIn("podman machine start", recipe)
        self.assertNotIn(
            "podman machine",
            re.sub(r"(?m)^#.*$", "", doctor_mk).split("podman-start:")[0],
        )
        self.assertIn("make podman-start", doctor_mk)

    def test_apm_runs_in_a_pinned_image_behind_a_target(self):
        """id: R-16"""
        tools = (self.SETUP / "tools.mk").read_text(encoding="utf-8")
        image = re.search(r"^APM_IMAGE \?= (\S+)$", tools, re.M).group(1)
        version = re.search(r"^APM_VERSION \?= (\S+)$", tools, re.M).group(1)
        self.assertIn("$(APM_IMAGE)", tools)
        self.assertIn('"apm-cli==$(APM_VERSION)"', tools)
        skills = (self.SETUP / "skills.mk").read_text(encoding="utf-8")
        for target in ("skills-install:", "skills-update:", "apm:"):
            self.assertIn("\n" + target + " ## ", skills)
        self.assertIn("$(APM) install $(if $(DRY_RUN),--dry-run)", skills)
        self.assertIn("$(APM) update $(if $(DRY_RUN),--dry-run,--yes)", skills)
        project = (self.SETUP / "project.mk").read_text(encoding="utf-8")
        self.assertIn("include $(PROJECT_MK_DIR)skills.mk", project)
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("project-setup/skills.mk", sdlc)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        start = [line for line in readme.splitlines() if "apm install'" in line]
        self.assertEqual(len(start), 1)
        self.assertTrue(start[0].strip().startswith("podman run --rm "))
        self.assertIn(f" {image} ", start[0])
        self.assertIn(f"apm-cli=={version} ", start[0])

    def test_the_readme_updates_the_skills_through_make(self):
        """id: R-72"""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Run `make skills-update`.", readme)
        self.assertIn("`make skills-update DRY_RUN=1`", readme)
        self.assertNotIn("Run `apm update`", readme)
        self.assertNotIn("run `apm install`", readme)

    def test_the_readme_defines_the_test_in_a_test_repository(self):
        """id: R-100"""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Test the collection in a test repository", readme)
        for branch in ("claude/framework-test-base", "claude/framework-test"):
            self.assertIn(f"`{branch}`", readme)
        self.assertIn(
            "Never push to or change the default branch (`main`) of the test repository.",
            readme,
        )
        self.assertIn(
            "Never delete a release, a tag, or a package version for real."
            " Run a cleanup target only with `DRY_RUN=1`.",
            readme,
        )
        self.assertIn("Work only on the two test branches.", readme)
        self.assertIn(
            "make pull-request-merge WAIT=1 DEFAULT_BRANCH=claude/framework-test-base",
            readme,
        )
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn('-f base="$(DEFAULT_BRANCH)"', sdlc)

    def test_old_board_is_a_target_and_migrate_docs_types_no_host_command(self):
        """id: R-21"""
        board = (self.SETUP / "old-board.mk").read_text(encoding="utf-8")
        paths = re.search(r"^OLD_BOARD_PATHS := (.+)$", board, re.M).group(1).split()
        self.assertEqual(
            paths,
            [
                "docs/BUGS.md",
                "docs/WAVES.md",
                "docs/FEATURES.md",
                "docs/DECISIONS.md",
                "docs/KNOWN_ISSUES.md",
                "docs/bugs",
                "docs/waves",
                "docs/features",
            ],
        )
        self.assertIn("\nold-board: ## ", board)
        self.assertIn("exit 1", board)
        migrate = (ROOT / "skills" / "migrate-docs" / "migrate.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("project-setup/old-board.mk", migrate)
        self.assertIn("\nold-board-delete: ## ", migrate)
        project = (self.SETUP / "project.mk").read_text(encoding="utf-8")
        self.assertIn("include $(PROJECT_MK_DIR)old-board.mk", project)
        self.assertIn("-include .claude/skills/migrate-docs/migrate.mk", project)
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("project-setup/old-board.mk", sdlc)
        self.assertIn("-include .claude/skills/migrate-docs/migrate.mk", sdlc)
        skill = (ROOT / "skills" / "migrate-docs" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`make old-board`", skill)
        self.assertIn("`make old-board-delete`", skill)
        self.assertNotIn("ls -d", skill)
        self.assertNotIn("rmdir", skill)
        for path in ("docs/DECISIONS.md", "docs/KNOWN_ISSUES.md"):
            self.assertIn(path, skill)

    def test_old_board_fails_on_the_old_line_form_of_the_roadmap(self):
        """id: R-21"""
        board = (self.SETUP / "old-board.mk").read_text(encoding="utf-8")
        lines = [
            line
            for line in board.splitlines()
            if "docs/ROADMAP.md" in line and line.lstrip().startswith("if [ -f")
        ]
        self.assertEqual(len(lines), 1)
        check = lines[0].strip().removesuffix("\\")
        cases = (
            ("- H-1: the old line form\n", "1"),
            ("# Roadmap\n\n| Id | Kind |\n| --- | --- |\n| W-1 | feature |\n", "0"),
            (None, "0"),
        )
        for text, expected in cases:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "docs").mkdir()
                if text is not None:
                    (Path(tmp) / "docs" / "ROADMAP.md").write_text(
                        text, encoding="utf-8"
                    )
                result = subprocess.run(
                    ["sh", "-c", f"found=0; {check} echo $found"],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    check=True,
                )
            self.assertEqual(result.stdout.strip().splitlines()[-1], expected)
        self.assertIn("old roadmap form", lines[0])

    def test_the_github_cli_runs_in_podman_with_the_token_of_the_environment(self):
        """id: R-99"""
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertRegex(sdlc, r"(?m)^GH_VERSION \?= \d+\.\d+\.\d+$")
        self.assertRegex(sdlc, r"(?m)^GH_BASE_IMAGE \?= \S+:\S+$")
        gh = re.search(r"^GH = (.+)$", sdlc, re.M).group(1)
        self.assertTrue(gh.startswith("podman run --rm "))
        self.assertIn("-e GH_TOKEN -e GITHUB_TOKEN", gh)
        self.assertTrue(gh.endswith("$(GH_IMAGE)"))
        self.assertIn("\ngh-image: ## ", sdlc)
        self.assertEqual(sdlc.count("$(GH) api"), 13)
        self.assertEqual(host_calls(self.PIPELINE / "sdlc.mk"), [])
        for target in (
            "cleanup-container-versions",
            "cleanup-github-releases",
            "cleanup-actions-artifacts",
        ):
            recipe = sdlc.split("\n" + target + ": ## ")[1].split("\n\n")[0]
            self.assertIn("$(THIS_MAKE) --no-print-directory gh-image", recipe)
            self.assertIn("$(GH) api", recipe)
        gradle = (self.PIPELINE / "templates" / "Makefile.gradle").read_text(
            encoding="utf-8"
        )
        self.assertEqual(gradle.count("$(GH) release"), 3)
        self.assertEqual(gradle.count('-R "$(PACKAGE)"'), 3)
        for name in ("ci.make.yml", "ci.node.yml", "ci.gradle.yml"):
            workflow = (self.PIPELINE / "templates" / name).read_text(encoding="utf-8")
            runs = re.findall(r"^\s+(?:- )?run: (.+)$", workflow, re.M)
            self.assertGreater(len(runs), 8)
            for run in runs:
                self.assertRegex(run, r"^make [a-z-]+$")
            self.assertIn("GH_TOKEN: ${{ github.token }}", workflow)

    CONTRACT_TARGETS = (
        "setup",
        "build",
        "test",
        "editorconfig",
        "format",
        "format-fix",
        "lint",
        "integration",
        "coverage",
        "test-changed",
        "docs",
        "login",
    )

    def test_the_pipeline_templates_set_command_variables_and_no_contract_target(
        self,
    ):
        """id: R-23 R-71"""
        variables = (
            "SETUP_CMD",
            "BUILD_CMD",
            "TEST_CMD",
            "FORMAT_CMD",
            "FORMAT_FIX_CMD",
            "LINT_CMD",
            "INTEGRATION_CMD",
            "COVERAGE_CMD",
            "TEST_CHANGED_CMD",
            "DOCS_CMD",
        )
        for name in ("Makefile.node", "Makefile.gradle"):
            text = (self.PIPELINE / "templates" / name).read_text(encoding="utf-8")
            include = text.index("include .claude/skills/github-pipeline/sdlc.mk")
            for variable in variables:
                match = re.search(rf"(?m)^{variable} = ", text)
                self.assertIsNotNone(match, f"{name} {variable}")
                self.assertLess(match.start(), include, f"{name} {variable}")
            for variable in ("RENDER_DOCS = 1", "PUBLISH_IMAGE = 1"):
                self.assertLess(text.index(variable), include, f"{name} {variable}")
            for target in self.CONTRACT_TARGETS:
                self.assertNotRegex(text, rf"(?m)^{target}:", f"{name} {target}")
            self.assertNotIn("project-setup/project.mk", text)

    def test_no_file_of_a_skill_names_the_own_contract_switch(self):
        """id: R-23"""
        switch = "SDLC_OWN" + "_CONTRACT"
        found = []
        for path in sorted((ROOT / "skills").rglob("*")):
            if not path.is_file() or path.suffix in (".pyc", ".toon"):
                continue
            if switch in path.read_text(encoding="utf-8", errors="ignore"):
                found.append(str(path))
        self.assertEqual(found, [])

    def test_the_summary_of_a_pipeline_command_writes_a_hash_as_backslash_hash(self):
        """id: R-71"""
        for name in ("Makefile.node", "Makefile.gradle"):
            text = (self.PIPELINE / "templates" / name).read_text(encoding="utf-8")
            lines = [
                line
                for line in text.splitlines()
                if re.search(r"> build/summaries/(setup|build|test|docs)\.md", line)
            ]
            self.assertGreaterEqual(len(lines), 3, name)
            for line in lines:
                self.assertIn("printf '\\# ", line, f"{name}: {line}")

    def test_the_empty_command_check_of_the_contract_is_made_by_make(self):
        """id: R-71"""
        contract = (self.SETUP / "contract.mk").read_text(encoding="utf-8")
        for variable in ("SETUP_CMD", "BUILD_CMD", "DOCS_CMD"):
            self.assertIn(f"ifeq ($(strip $({variable})),)", contract)
            self.assertNotIn(f'-z "$({variable})"', contract)

    def test_the_image_targets_of_the_pipeline_take_their_context_from_variables(
        self,
    ):
        """id: R-71"""
        container = (self.PIPELINE / "container.mk").read_text(encoding="utf-8")
        for variable in ("IMAGE_CONTEXT", "IMAGE_PREPARE", "PUBLISH_PREPARE"):
            self.assertRegex(container, rf"(?m)^{variable} \?= ")
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("\ninclude $(SDLC_MK_DIR)container.mk\n", sdlc)
        self.assertIn("\ninclude $(SDLC_MK_DIR)../project-setup/contract.mk\n", sdlc)
        gradle = (self.PIPELINE / "templates" / "Makefile.gradle").read_text(
            encoding="utf-8"
        )
        for variable in ("IMAGE_CONTEXT", "IMAGE_PREPARE", "PUBLISH_PREPARE"):
            self.assertRegex(gradle, rf"(?m)^{variable} = ")
        node = (self.PIPELINE / "templates" / "Makefile.node").read_text(
            encoding="utf-8"
        )
        self.assertIn("image-ci", node.split("\nBUILD_CMD = ")[1].split("\n\n")[0])
        self.assertRegex(node, r"(?m)^SMOKE_CMD = ")

    def test_jvm_tooling_counts_a_kotlin_build_file_as_present(self):
        """id: R-66"""
        gradle = (ROOT / "skills" / "jvm" / "templates" / "Makefile.gradle").read_text(
            encoding="utf-8"
        )
        recipe = gradle.split("\njvm-tooling: ## ")[1].split("\n\n")[0]
        self.assertIn(
            "if [ ! -f build.gradle ] && [ ! -f build.gradle.kts ]; then cp", recipe
        )
        self.assertIn(
            "if [ ! -f settings.gradle ] && [ ! -f settings.gradle.kts ]; then sed",
            recipe,
        )

    def test_a_failed_project_report_leaves_no_report_file(self):
        """id: R-75"""
        for name in ("project-report/report.mk", "project-setup/contract.mk"):
            text = (ROOT / "skills" / name).read_text(encoding="utf-8")
            self.assertIn("> build/project-report.md.tmp ||", text, name)
            self.assertIn(
                "mv build/project-report.md.tmp build/project-report.md", text
            )

    def test_the_diff_base_falls_back_to_the_local_default_branch(self):
        """id: R-12"""
        base = "git merge-base HEAD $(DEFAULT_BRANCH) 2>/dev/null || git rev-parse"
        paths = list(ROOT.glob("skills/*/templates/Makefile.*"))
        paths.append(ROOT / "skills/project-setup/test-changed.mk")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "git merge-base" in text:
                self.assertIn(base, text, str(path))

    def test_make_finds_the_default_branch_without_an_override(self):
        """id: R-12"""
        text = (ROOT / "skills/project-setup/tools.mk").read_text(encoding="utf-8")
        self.assertIn("ifndef DEFAULT_BRANCH", text)
        for source in (
            "refs/remotes/origin/HEAD",
            "refs/heads/main",
            "refs/heads/master",
        ):
            self.assertIn(source, text)

    def test_the_github_targets_stop_without_a_token_and_without_a_tag(self):
        """id: R-75"""
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        define = sdlc.split("define SDLC_GH_REPO\n")[1].split("\nendef")[0]
        self.assertIn("GH_TOKEN:-}$${GITHUB_TOKEN:-}", define)
        tags = sdlc.split("\npublish-tags: ## ")[1].split("\n\n")[0]
        self.assertIn("tag=$$($(THIS_MAKE) -s --no-print-directory version);", tags)
        self.assertNotIn('"$$($(THIS_MAKE)', tags)

    def test_the_ci_result_and_the_pull_request_run_in_the_github_cli_image(self):
        """id: R-75"""
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        for target in ("ci-status", "pull-request", "pull-request-merge"):
            self.assertRegex(sdlc, rf"(?m)^{target}: ## \S")
            recipe = sdlc.split("\n" + target + ": ## ")[1].split("\n\n")[0]
            self.assertIn("$(THIS_MAKE) --no-print-directory gh-image", recipe)
            self.assertIn("$(SDLC_GH_REPO)", recipe)
            self.assertNotIn("git remote", recipe)
        define = sdlc.split("define SDLC_GH_REPO\n")[1].split("\nendef")[0]
        self.assertIn('repo="$(GH_REPO)"', define)
        self.assertRegex(sdlc, r"(?m)^GH_REPO \?= \$\(OWNER\)/\$\(NAME\)$")
        status = sdlc.split("\nci-status: ## ")[1].split("\n\n")[0]
        self.assertIn('$(GH) run list -R "$$repo" --commit "$$sha"', status)
        self.assertIn('"$${WAIT:-}" != 1', status)
        self.assertIn('if [ "$$result" != success ]; then exit 1; fi', status)
        opened = sdlc.split("\npull-request: ## ")[1].split("\n\n")[0]
        self.assertIn("$(SDLC_BRANCH)", opened)
        self.assertIn('$(GH) api "repos/$$repo/pulls?head=', opened)
        self.assertIn('$(GH) api -X POST "repos/$$repo/pulls"', opened)
        self.assertLess(opened.index("pulls?head="), opened.index("-X POST"))
        self.assertLess(opened.index("exit 0"), opened.index("-X POST"))
        merge = sdlc.split("\npull-request-merge: ## ")[1].split("\n\n")[0]
        self.assertIn('"repos/$$repo/commits/$$sha/check-runs', merge)
        self.assertIn('"$$total" -eq 0', merge)
        self.assertIn('$(GH) api -X PUT "repos/$$repo/pulls/$$number/merge"', merge)
        self.assertIn("-f merge_method=merge", merge)
        self.assertLess(merge.index("check-runs"), merge.index("-X PUT"))
        for target in ("pull-request", "pull-request-merge"):
            recipe = sdlc.split("\n" + target + ": ## ")[1].split("\n\n")[0]
            self.assertNotIn("$(GH) pr ", recipe)
        branch = sdlc.split("define SDLC_BRANCH\n")[1].split("\nendef")[0]
        self.assertIn('"$(DEFAULT_BRANCH)"', branch)
        self.assertEqual(host_calls(self.PIPELINE / "sdlc.mk"), [])
        listing = (self.PIPELINE / "references" / "makefile.md").read_text(
            encoding="utf-8"
        )
        for target in ("ci-status", "pull-request", "pull-request-merge"):
            self.assertIn(f"| `{target}` |", listing)


PIPELINE_MK = ROOT / "skills" / "github-pipeline" / "sdlc.mk"

FAKE_GH = """\
printf '%s\\n' "$*" >> calls.log
case "$*" in
    *"-X DELETE"*) ;;
    *"/versions?per_page"*) cat versions.tsv ;;
    *"/releases?per_page"*) cat releases.tsv ;;
    *"users/"*) echo User ;;
esac
"""

# Columns: id, created_at, tags.
PACKAGE_VERSIONS = (
    ("10", "2025-01-01T00:00:00Z", "1.2.0-1"),
    ("11", "2025-01-02T00:00:00Z", "1.2.0-2"),
    ("12", "2025-01-03T00:00:00Z", "1.2.0-3"),
    ("13", "2025-01-04T00:00:00Z", "1.2.0-4"),
    ("14", "2025-01-05T00:00:00Z", "1.2.0-5,latest"),
    ("15", "2025-01-06T00:00:00Z", "sha-abc"),
    ("17", "2024-12-01T00:00:00Z", "1.1.0-9"),
)

# Columns: id, tag_name, created_at. v1.2.0 is the newest and is no build.
RELEASES = (
    ("20", "1.2.0-1", "2025-01-01T00:00:00Z"),
    ("21", "1.2.0-2", "2025-01-02T00:00:00Z"),
    ("22", "1.2.0-3", "2025-01-03T00:00:00Z"),
    ("23", "v1.2.0", "2025-01-10T00:00:00Z"),
)


def expand_make_recipe(target, variables):
    """The shell text that Make hands to sh for a recipe of sdlc.mk.

    Make is not in the test image. This reads the recipe of the target and
    the two define blocks it expands, and replaces `$(NAME)` from
    `variables` and `$$` with `$`. An unknown `$(NAME)` fails the test.
    """
    text = PIPELINE_MK.read_text(encoding="utf-8")
    recipe = text.split("\n" + target + ": ## ")[1].split("\n\n")[0]
    recipe = recipe.split("\n", 1)[1]
    lines = [line[1:] if line.startswith("\t") else line for line in recipe.split("\n")]
    shell = "\n".join(lines).replace("@set -eu;", "set -eu;", 1)
    for name in ("SDLC_ON_DEFAULT", "SDLC_TAG"):
        body = text.split(f"define {name}\n")[1].split("\nendef")[0]
        shell = shell.replace(f"$({name})", body)
    shell = shell.replace("$(THIS_MAKE) --no-print-directory gh-image", "true")

    def replace(match):
        if match.group(1) is None:
            return "$"
        return variables[match.group(1)]

    return re.sub(r"\$\$|\$\((\w+)\)", replace, shell)


class CleanupRecipeTest(unittest.TestCase):
    """Runs the real recipes of sdlc.mk in sh against a fake GitHub CLI."""

    def run_cleanup(self, target, rows, env=None, dry_run="", tag="", version=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gh.sh").write_text(FAKE_GH, encoding="utf-8")
            listing = "".join("\t".join(row) + "\n" for row in rows)
            name = "versions.tsv" if "versions" in target else "releases.tsv"
            (root / name).write_text(listing, encoding="utf-8")
            if version is not None:
                (root / "build").mkdir()
                (root / "build" / "publish-version.txt").write_text(
                    version + "\n", encoding="utf-8"
                )
            variables = {
                "GH": f"sh {root / 'gh.sh'}",
                "IMAGE": "ghcr.io/acme/app",
                "PACKAGE": "acme/app",
                "KEEP_VERSIONS": "2",
                "DRY_RUN": dry_run,
                "PUBLISHED_TAG": tag,
            }
            shell = expand_make_recipe(target, variables)
            environment = {"PATH": os.environ["PATH"], **(env or {})}
            result = subprocess.run(
                ["sh", "-c", shell],
                cwd=tmp,
                env=environment,
                capture_output=True,
                text=True,
            )
            calls = root / "calls.log"
            lines = (
                calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
            )
            fields = dict(
                line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
            )
            return result, lines, fields

    def deleted(self, calls):
        return [line for line in calls if "-X DELETE" in line]

    def test_a_cleanup_without_a_tag_keeps_the_newest_rolling_version(self):
        """id: R-96"""
        result, calls, fields = self.run_cleanup(
            "cleanup-container-versions", PACKAGE_VERSIONS, dry_run="1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(fields["status"], "dry-run")
        self.assertEqual(fields["kept"], "2")
        self.assertEqual(fields["deleted"], "4")
        self.assertIn("Kept 1.2.0-5 ", fields["reason"])
        for version in ("10", "11", "12", "17"):
            self.assertIn(f"would delete package version {version}\n", result.stdout)
        for version in ("13", "14", "15"):
            self.assertNotIn(f"would delete package version {version}\n", result.stdout)
        self.assertEqual(self.deleted(calls), [])

    def test_a_cleanup_without_a_tag_deletes_on_a_laptop(self):
        """id: R-96"""
        for target, rows, expected in (
            ("cleanup-container-versions", PACKAGE_VERSIONS, ("10", "11", "12", "17")),
            ("cleanup-github-releases", RELEASES, ("20",)),
        ):
            result, calls, fields = self.run_cleanup(target, rows)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fields["status"], "deleted", target)
            removed = self.deleted(calls)
            for ident in expected:
                self.assertTrue(
                    any(f"/{ident}" in line for line in removed), (target, ident)
                )
            self.assertEqual(
                len(removed), len(expected) * (2 if "releases" in target else 1)
            )
            self.assertFalse(any("/13" in line or "/14" in line for line in removed))
            self.assertFalse(any("/23" in line for line in removed))

    def test_a_dry_run_of_the_releases_prints_and_deletes_nothing(self):
        """id: R-96"""
        result, calls, fields = self.run_cleanup(
            "cleanup-github-releases", RELEASES, dry_run="1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(fields["status"], "dry-run")
        self.assertIn("would delete release 1.2.0-1\n", result.stdout)
        self.assertNotIn("would delete release v1.2.0", result.stdout)
        self.assertEqual(self.deleted(calls), [])

    def test_a_given_tag_decides_the_kept_version_and_names_its_source(self):
        """id: R-96"""
        for source in ("PUBLISHED_TAG", "build/publish-version.txt"):
            kwargs = {"tag": "1.2.0-4"} if source == "PUBLISHED_TAG" else {}
            if source != "PUBLISHED_TAG":
                kwargs["version"] = "1.2.0-4"
            result, calls, fields = self.run_cleanup(
                "cleanup-container-versions", PACKAGE_VERSIONS, dry_run="1", **kwargs
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Kept 1.2.0-4 ", fields["reason"], source)
            self.assertIn("would delete package version 10\n", result.stdout)
            self.assertNotIn("would delete package version 12\n", result.stdout)
            bad = {"tag": "1.2.0-99"} if source == "PUBLISHED_TAG" else {}
            if source != "PUBLISHED_TAG":
                bad["version"] = "1.2.0-99"
            for target, rows in (
                ("cleanup-container-versions", PACKAGE_VERSIONS),
                ("cleanup-github-releases", RELEASES),
            ):
                result, calls, fields = self.run_cleanup(target, rows, **bad)
                self.assertNotEqual(result.returncode, 0, (target, source))
                self.assertIn(f"from {source} is not exactly one", result.stderr)
                self.assertEqual(self.deleted(calls), [])
        result, _calls, _fields = self.run_cleanup(
            "cleanup-container-versions", PACKAGE_VERSIONS, tag="1.2.0"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("from PUBLISHED_TAG is not MAJOR.MINOR.PATCH-run", result.stderr)

    def test_a_list_without_a_rolling_version_deletes_nothing_and_exits_zero(self):
        """id: R-96"""
        only_fixed = (
            ("30", "2025-01-01T00:00:00Z", "latest"),
            ("31", "2025-01-02T00:00:00Z", "sha-abc"),
        )
        for target, rows in (
            ("cleanup-container-versions", only_fixed),
            ("cleanup-github-releases", (("40", "v1.0.0", "2025-01-01T00:00:00Z"),)),
            ("cleanup-github-releases", ()),
        ):
            result, calls, fields = self.run_cleanup(target, rows)
            self.assertEqual(result.returncode, 0, (target, result.stderr))
            self.assertEqual(fields["status"], "kept", target)
            self.assertEqual(fields["deleted"], "0")
            self.assertEqual(self.deleted(calls), [])

    def test_ci_deletes_only_on_the_default_branch(self):
        """id: R-96"""
        other = {"GITHUB_REF": "refs/heads/feature", "SDLC_DEFAULT_BRANCH": "main"}
        main = {"GITHUB_REF": "refs/heads/main", "SDLC_DEFAULT_BRANCH": "main"}
        for target, rows in (
            ("cleanup-container-versions", PACKAGE_VERSIONS),
            ("cleanup-github-releases", RELEASES),
        ):
            result, calls, fields = self.run_cleanup(target, rows, env=other)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fields["status"], "kept", target)
            self.assertEqual(calls, [])
            result, calls, fields = self.run_cleanup(target, rows, env=main)
            self.assertEqual(fields["status"], "deleted", target)
            self.assertTrue(self.deleted(calls), target)

    def test_the_tag_of_a_cleanup_never_calls_version(self):
        """id: R-96"""
        text = PIPELINE_MK.read_text(encoding="utf-8")
        body = text.split("define SDLC_TAG\n")[1].split("\nendef")[0]
        self.assertNotIn("$(THIS_MAKE)", body)
        self.assertNotIn("GITHUB_RUN_NUMBER", body)
        for target in ("cleanup-container-versions", "cleanup-github-releases"):
            recipe = text.split("\n" + target + ": ## ")[1].split("\n\n")[0]
            self.assertIn("$(SDLC_TAG)", recipe)
            self.assertNotIn("-s --no-print-directory version", recipe)


if __name__ == "__main__":
    unittest.main()
