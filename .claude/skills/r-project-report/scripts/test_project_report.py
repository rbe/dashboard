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
from xml.etree import ElementTree

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
skill_index = load("skill_index", ROOT / "skills/r-record/scripts/skill_index.py")


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
        record = (ROOT / "skills" / "r-record" / "SKILL.md").read_text(encoding="utf-8")
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
                ".claude/skills/r-record/scripts/test_record.py",
                'def test_runs():\n    """id: R-13"""\n    assert True\n',
            )
            write(root, "node_modules/x/x.test.js", "test('x', () => {})\n")
            write(
                root,
                "apm_modules/rbe/ralfskills/skills/r-record/scripts/test_record.py",
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
        setup = ROOT / "skills" / "r-project-setup"
        fragment = (setup / "test-changed.mk").read_text(encoding="utf-8")
        self.assertIn("test-changed:", fragment)
        project = (setup / "project.mk").read_text(encoding="utf-8")
        self.assertIn("include $(PROJECT_MK_DIR)test-changed.mk", project)
        sdlc = (ROOT / "skills" / "r-github-pipeline" / "sdlc.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("r-project-setup/test-changed.mk", sdlc)
        ci_targets = [line for line in sdlc.splitlines() if line.startswith("SDLC_CI")]
        self.assertEqual(len(ci_targets), 1)
        self.assertNotIn("test-changed", ci_targets[0])
        develop = (ROOT / "skills" / "r-develop" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("A green `test-changed` does not replace `make test`.", develop)
        for name in ("ci.node.yml", "ci.gradle.yml"):
            workflow = (
                ROOT / "skills" / "r-github-pipeline" / "templates" / name
            ).read_text(encoding="utf-8")
            self.assertIn("\n      - run: make test\n", workflow)
            self.assertNotIn("test-changed", workflow)


ENTRY_FILES = ("CLAUDE.md", "skills/r-project-setup/templates/CLAUDE.md")


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
        owners = {
            path.name.removeprefix("r-")
            for path in (ROOT / "skills").iterdir()
            if path.is_dir()
        }
        for path in self.files():
            self.assertIn(path.stem, owners | {"collection"}, path.name)

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


class AgentAgnosticTextTest(unittest.TestCase):
    def test_no_skill_text_names_an_ai_coding_tool_a_tool_folder_or_a_model(self):
        """id: R-17"""
        names = (
            "Cursor",
            ".agents/",
            ".cursor/",
            "Fable",
            "Opus",
            "Sonnet",
            "Haiku",
        )
        files = sorted((ROOT / "skills").glob("r-*/SKILL.md")) + sorted(
            (ROOT / "skills").glob("r-*/references/**/*.md")
        )
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for name in names:
                self.assertNotIn(name, text, str(path))


class StageRoutingTest(unittest.TestCase):
    def test_every_check_and_language_skill_names_the_stages_that_load_it(self):
        """id: R-110"""
        found = skill_index.rows(ROOT)
        self.assertTrue(found)
        self.assertIn("stages", skill_index.render(found).splitlines()[0])
        for row in found:
            self.assertTrue(row["stages"], row["name"])
            expected = (
                ["r-plan", "r-review"] if row["kind"] == "check" else ["r-develop"]
            )
            self.assertEqual(row["stages"], expected, row["name"])
            for stage in row["stages"]:
                self.assertTrue((ROOT / "skills" / stage / "SKILL.md").is_file(), stage)

    def test_a_stage_reads_the_stages_column_and_names_no_subskill(self):
        """id: R-110"""
        names = [row["name"] for row in skill_index.rows(ROOT)]
        for stage, column in (
            ("r-plan", "`stages` names `r-plan`"),
            ("r-review", "`stages` names `r-review`"),
            ("r-develop", "`stages` names `r-develop`"),
        ):
            steps = (ROOT / "skills" / stage / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(column, steps)
            for name in names:
                self.assertNotIn(f"`{name}`", steps, f"{stage} names {name}")


class ReviewRulesTest(unittest.TestCase):
    def skill(self, name):
        return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    def test_the_defect_report_form_has_eight_parts_with_one_owner(self):
        """id: R-113"""
        form = (ROOT / "skills/r-record/references/defect-report.md").read_text(
            encoding="utf-8"
        )
        for number, part in enumerate(
            (
                "Location:",
                "Mechanism:",
                "Evidence:",
                "Not a regression:",
                "The rule it contradicts:",
                "Fix options:",
                "Acceptance check:",
                "Documents to update:",
            ),
            1,
        ):
            self.assertIn(f"\n{number}. {part}", form)
        self.assertIn("references/defect-report.md", self.skill("r-record"))
        review = self.skill("r-review")
        self.assertIn("the defect report form of `r-record`", review)
        self.assertNotIn("the mechanism", review)

    def test_only_the_release_skill_states_the_staging_rule(self):
        """id: R-114"""
        rule = "Never run `git add -A`, `git add .`, or `git commit -a`."
        self.assertIn(
            "Stage only the files of the change, by name.", self.skill("r-release")
        )
        self.assertIn(rule, self.skill("r-release"))
        for path in (ROOT / "skills").glob("r-*/SKILL.md"):
            if path.parent.name != "r-release":
                self.assertNotIn("git add -A", path.read_text(encoding="utf-8"))


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
        limits = {"CLAUDE.md": 966, "skills/r-project-setup/templates/CLAUDE.md": 1036}
        for name, limit in limits.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertLessEqual(len(text.split()), limit, name)

    def test_the_entry_file_and_its_template_have_the_agents_section(self):
        """id: R-109"""
        for name in ENTRY_FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("\n## Agents\n"), 1, name)
            self.assertLess(text.index("</general_rules>"), text.index("\n## Agents\n"))
            self.assertLess(
                text.index("\n## Agents\n"), text.index("\n## Communication contract\n")
            )
            section = text[text.index("\n## Agents\n") :]
            section = section[: section.index("\n## Communication contract\n")]
            for phrase in (
                "Fable or Opus",
                "Sonnet implements normal work.",
                "Haiku implements mechanical work.",
                "re-checks each claim of an agent",
                "fails twice on one step",
                "names no model and has no `model:` field",
                "names a model alias",
            ):
                self.assertIn(phrase, section, name)

    def test_no_skill_has_a_model_field(self):
        """id: R-109"""
        for path in sorted((ROOT / "skills").glob("r-*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            frontmatter = text[3 : text.index("\n---", 3)]
            for line in frontmatter.splitlines():
                self.assertFalse(line.startswith("model:"), str(path))

    def test_the_entry_file_and_its_template_state_the_stage_addendum_once(self):
        """id: R-112"""
        sentence = (
            "If `CLAUDE.md` lists a project skill `<project>-<stage>`, the stage "
            "reads it after its own steps. The addendum holds only what is true "
            "for that project."
        )
        for name in ENTRY_FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(text.count(sentence), 1, name)
        for path in (ROOT / "skills").glob("r-*/SKILL.md"):
            self.assertNotIn("<stage>", path.read_text(encoding="utf-8"), str(path))

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
            self.assertIn("the only skill is `r-migrate-docs`", text)
            self.assertIn("`r-record` writes every id and every board document.", text)
            self.assertIn("Run `make toon` before you read an index.", text)

    def test_a_requirements_repository_reads_the_requirements_index(self):
        """id: R-54"""
        for text in general_rules():
            self.assertIn(
                "Where a step names `docs/adr/index.toon`, read "
                "`docs/requirements-index.toon` in such a repository",
                text,
            )
        for name in ("r-develop", "r-review"):
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
        self.assertEqual(len(skill_files()), 30)
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

    def test_each_skill_folder_and_name_start_with_r_and_agree(self):
        """id: R-105"""
        folders = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertTrue(folders)
        for folder in folders:
            self.assertTrue(folder.name.startswith("r-"), folder.name)
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(
                text, rf"\A---\nname: {re.escape(folder.name)}\n", folder.name
            )

    def test_only_migrate_docs_names_a_path_of_the_old_board(self):
        """id: R-21"""
        for path in skill_files():
            if path.parent.name == "r-migrate-docs":
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
            "skills/r-plan/SKILL.md",
            "---\nname: plan\n---\n\n<steps>\n1. Name who owns state.\n</steps>\n",
        )
        write(
            root,
            "skills/r-develop/SKILL.md",
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
            self.assertIn("r-project-setup: not installed", development)

    def test_the_reviews_read_the_checks_tag_of_project_setup(self):
        """id: R-3"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sample(root)
            write(
                root,
                "skills/r-project-setup/SKILL.md",
                '---\nname: r-project-setup\n---\n\n<mode name="setup">\n<steps>\n'
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
                "skills/r-review/SKILL.md",
                "# Review\n\n## Steps\n\n1. Not a check.\n\n## Work\n\n"
                "1. Run the gates.\n\n## Later\n\n1. Not a check.\n",
            )
            text, _errors = project_report.build(root)
            self.assertEqual(text.count("- 1. Run the gates."), 2)
            self.assertNotIn("Not a check.", text)

    def test_make_project_report_is_the_writer(self):
        """id: R-3"""
        for name in ("r-review", "r-project-setup", "r-project-report"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`make project-report`", text)
        report = (ROOT / "skills" / "r-project-report" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`make project-report` writes `build/project-report.md`", report)
        for text in general_rules():
            self.assertIn(
                "Hand-editing a file that a Make target writes is a defect.", text
            )
        contract = (ROOT / "skills" / "r-project-setup" / "contract.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("\nproject-report:", contract)

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
    SETUP = ROOT / "skills" / "r-project-setup"
    PIPELINE = ROOT / "skills" / "r-github-pipeline"

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
        index_mk = (ROOT / "skills/r-record/index.mk").read_text(encoding="utf-8")
        self.assertIn("ifdef DOCTOR_MK\ntoon: doctor\nendif", index_mk)
        for name in ("project.mk", "../r-github-pipeline/sdlc.mk"):
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
        self.assertIn("r-project-setup/skills.mk", sdlc)
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

    def test_the_readme_states_three_facts_for_the_migration_of_a_project(self):
        """id: R-72"""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("`make old-board` fails first, as designed", readme)
        self.assertIn("the only skill is then `r-migrate-docs`", readme)
        self.assertIn("APM calls them unmanaged", readme)
        self.assertIn("`make apm ARGS='install --force'`", readme)
        self.assertIn("`make ids` fails", readme)
        self.assertIn("`make id-raise KIND=<kind> TO=<n>`", readme)
        index = (ROOT / "skills" / "r-record" / "index.mk").read_text(encoding="utf-8")
        self.assertIn("id-raise:", index)
        skills = (self.SETUP / "skills.mk").read_text(encoding="utf-8")
        self.assertIn("apm: ##", skills)

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

    def test_the_readme_shows_the_two_diagrams_with_their_explanations(self):
        """id: R-101"""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        sections = {
            "collection-map.svg": "## How the parts work together",
            "board-map.svg": "## The cycle",
        }
        for name, heading in sections.items():
            path = ROOT / "docs" / "diagrams" / name
            svg = ElementTree.parse(path).getroot()
            self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIsNotNone(svg.find("{http://www.w3.org/2000/svg}title"))
            self.assertIn(
                "prefers-color-scheme: dark", path.read_text(encoding="utf-8")
            )
            section = readme.split(heading, 1)[1].split("\n## ", 1)[0]
            self.assertRegex(section, rf"!\[[^\]]+\]\(docs/diagrams/{name}\)")
            self.assertIn(f"The diagram is `docs/diagrams/{name}`.", section)
            self.assertIn("\n1. ", section)

    def skill_text(self, name):
        return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    def test_ux_ui_design_asks_and_checks_accessibility(self):
        """id: R-33"""
        text = self.skill_text("r-ux-ui-design")
        for sentence in (
            "4. Which control returns focus to which control when a dialog closes?",
            "5. Which state does the screen show, and what shows it besides colour?",
            "2. Focus is visible. Text and controls meet contrast level AA of WCAG 2.2.",
            "3. Each input has a programmatic label.",
            "4. A validation error is text next to its field, not only a colour.",
            "5. No state shows by colour alone.",
            "6. A decorative icon is hidden from assistive technology."
            " An icon-only control has an accessible name.",
            "7. No content flashes more than three times in one second.",
            "8. A dialog returns focus to the control that opened it.",
        ):
            self.assertIn(sentence, text)
        self.assertEqual(text.count("contrast"), 1)

    def test_upgrade_skills_update_one_component_with_a_baseline(self):
        """id: R-104"""
        text = self.skill_text("r-component-upgrade")
        for sentence in (
            "- One slice updates one component.",
            "2. If the component is this skill collection, follow the Update section"
            " of the README and stop here.",
            "5. Run the gates before the change. Keep the result as the baseline.",
            "- A pin names an exact version. A pin never names `latest`.",
            "- If the update is a major version step, `r-plan` runs first,"
            " because the step can change a rule.",
            "`r-upgrade-<language>-components`",
        ):
            self.assertIn(sentence, text)
        for language in ("node", "python", "java", "go"):
            name = f"r-upgrade-{language}-components"
            text = self.skill_text(name)
            self.assertIn(f"name: {name}\n", text)
            self.assertIn("r-component-upgrade", text)

    def test_observability_skill_asks_and_checks(self):
        """id: R-102"""
        text = self.skill_text("r-observability")
        self.assertIn("kind: check\norder: 50", text)
        self.assertIn(
            "`r-privacy` owns personal data in logs. `r-api-design` owns the error body.",
            text,
        )
        for sentence in (
            "1. What does the program print on start?",
            "2. Which failure can the user cause, and where does the user see it?",
            "1. On start, the program prints one line with the address it listens on"
            " and the data paths it uses.",
            "3. A hot path writes no log line for each request.",
            "4. A failure that the user can cause reaches the user as a visible error,"
            " not as a silent empty view.",
            "5. The program logs the cause of an unexpected failure once.",
        ):
            self.assertIn(sentence, text)
        self.assertNotIn("personal data in logs.", text.split("<rules>")[0])

    def test_performance_skill_owns_the_baseline_rule(self):
        """id: R-103"""
        text = self.skill_text("r-performance")
        self.assertIn("kind: check\norder: 60", text)
        rule = "A claim about speed, size, or model output quality needs a baseline from the same session."
        self.assertIn(rule, text)
        self.assertNotIn("baseline from the same session", self.skill_text("r-review"))
        for sentence in (
            "1. What is the largest input that the change must handle?",
            "1. Each file or row is read once for each request, not once for each loop step.",
            "2. An import or a parse runs in one pass.",
            "3. Aggregation runs where the data is, not in a client that must first fetch all of it.",
            "Both come from the same machine and the same session.",
        ):
            self.assertIn(sentence, text)

    def test_close_deletes_the_proposal_and_shortens_the_history_file(self):
        """id: R-106"""
        record = ROOT / "skills" / "r-record"
        close = (record / "references" / "close.md").read_text(encoding="utf-8")
        for sentence in (
            "4. If the slice started from a proposal, delete the file"
            " `docs/proposals/<id>.md`.",
            "5. Shorten the history file to at most 150 words below its frontmatter.",
            "Keep what changed, the ids, the gate results, and what was not run.",
        ):
            self.assertIn(sentence, close)
        self.assertNotIn("status to `done`", close)
        kinds = (record / "references" / "id-kinds.md").read_text(encoding="utf-8")
        self.assertIn("The status is `open` or `started`.", kinds)
        self.assertNotIn("`done`", kinds)
        merge = self.skill_text("r-board-merge") + self.skill_text(
            "r-board-merge-report"
        )
        self.assertNotIn("150 words", merge)
        self.assertNotIn("proposal gets the status", merge)

    def test_skills_review_reports_three_kinds_and_names_the_owner_rule(self):
        """id: R-107"""
        text = self.skill_text("r-skills-review")
        kinds = self.skill_text("r-skills-review").split("<references>")[0]
        for sentence in (
            "- A pointer is not an overlap.",
            "- The owner rule: a rule that the general rules of `CLAUDE.md` state"
            " stays only there.",
            "Any other rule belongs to the skill whose purpose names the subject."
            " The other places keep a pointer.",
            "- Write each place as `path:line` and quote at most 20 words.",
            "- Change no file.",
            "This skill covers skill files only."
            " `r-board-merge-report` covers the board documents in `docs/`.",
        ):
            self.assertIn(sentence, kinds)
        for kind in (
            "Same rule in two places",
            "Same action in two skills",
            "Contradiction",
        ):
            self.assertIn(kind, text)
        self.assertIn(
            "`r-skills-review` covers skill files.",
            self.skill_text("r-board-merge-report"),
        )
        for name in ENTRY_FILES:
            self.assertIn(
                "`r-skills-review`", (ROOT / name).read_text(encoding="utf-8")
            )

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
        migrate = (ROOT / "skills" / "r-migrate-docs" / "migrate.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("r-project-setup/old-board.mk", migrate)
        self.assertIn("\nold-board-delete: ## ", migrate)
        project = (self.SETUP / "project.mk").read_text(encoding="utf-8")
        self.assertIn("include $(PROJECT_MK_DIR)old-board.mk", project)
        self.assertIn("-include .claude/skills/r-migrate-docs/migrate.mk", project)
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("r-project-setup/old-board.mk", sdlc)
        self.assertIn("-include .claude/skills/r-migrate-docs/migrate.mk", sdlc)
        skill = (ROOT / "skills" / "r-migrate-docs" / "SKILL.md").read_text(
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
            include = text.index("include .claude/skills/r-github-pipeline/sdlc.mk")
            for variable in variables:
                match = re.search(rf"(?m)^{variable} = ", text)
                self.assertIsNotNone(match, f"{name} {variable}")
                self.assertLess(match.start(), include, f"{name} {variable}")
            for variable in ("RENDER_DOCS = 1", "PUBLISH_IMAGE = 1"):
                self.assertLess(text.index(variable), include, f"{name} {variable}")
            for target in self.CONTRACT_TARGETS:
                self.assertNotRegex(text, rf"(?m)^{target}:", f"{name} {target}")
            self.assertNotIn("r-project-setup/project.mk", text)

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
        self.assertIn("\ninclude $(SDLC_MK_DIR)../r-project-setup/contract.mk\n", sdlc)
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

    def test_a_template_publishes_no_host_port_of_1024_or_lower(self):
        """id: R-115"""
        publish = re.compile(r"(?:-p|--publish)[ =](?:[0-9.]+:)?(\$\(\w+\)|\d+):")
        found = 0
        for path in self.makefiles():
            text = path.read_text(encoding="utf-8")
            for match in publish.finditer(text):
                found += 1
                host = match.group(1)
                if host.startswith("$("):
                    name = host[2:-1]
                    default = re.search(rf"(?m)^{name} \??= (\d+)$", text)
                    self.assertIsNotNone(default, f"{path.name} {name}")
                    host = default.group(1)
                self.assertGreater(int(host), 1024, f"{path.name}: {match.group(0)}")
        self.assertGreaterEqual(found, 1)
        node = (self.PIPELINE / "templates" / "Makefile.node").read_text(
            encoding="utf-8"
        )
        self.assertIn("-p 127.0.0.1:$(HOST_PORT):$(PORT)", node)
        self.assertIn('test "$(HOST_PORT)" -gt 1024', node)
        skill = (self.PIPELINE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "- A container uses a standard port inside. A host binding of `make run`"
            " uses a port above 1024, for example 8443, so no root privileges are"
            " needed.",
            skill,
        )

    def test_gradle_runs_in_podman_and_reaches_the_podman_socket(self):
        """id: R-116"""
        templates = {
            "r-jvm": ROOT / "skills" / "r-jvm" / "templates" / "Makefile.gradle",
            "r-github-pipeline": self.PIPELINE / "templates" / "Makefile.gradle",
        }
        jvm = (ROOT / "skills" / "r-jvm" / "jvm.mk").read_text(encoding="utf-8")
        self.assertRegex(jvm, r"(?m)^PODMAN_SOCKET \?= ")
        self.assertRegex(jvm, r"(?m)^podman-socket: ")
        for owner, path in templates.items():
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^PODMAN_SOCKET", owner)
            podman = re.search(r"(?m)^GRADLE_PODMAN = (?:.*\\\n)*.*$", text)
            self.assertIsNotNone(podman, owner)
            for part in (
                "--network host",
                "-e CONTAINER_HOST=unix:///run/podman/podman.sock",
                '-v "$(PODMAN_SOCKET)":/run/podman/podman.sock',
                "./gradlew",
            ):
                self.assertIn(part, podman.group(0), f"{owner} {part}")
            self.assertNotRegex(text, r"(?m)^podman-socket: ", owner)
            self.assertNotIn("docker.sock", text, owner)
            self.assertNotRegex(text, r"(?m)^[^#\n]*\bdocker run\b", owner)
        skill = (ROOT / "skills" / "r-jvm" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "- Gradle runs in a container and reaches Podman through"
            " `$(GRADLE_PODMAN)`, so the host needs no Java toolchain.",
            skill,
        )

    def test_a_client_package_has_one_generic_publish_workflow(self):
        """id: R-117"""
        text = (self.PIPELINE / "templates" / "publish-client.yml").read_text(
            encoding="utf-8"
        )
        for part in (
            "name: Publish client\n",
            "  workflow_dispatch:\n",
            '      - "client-v*"\n',
            "  contents: write\n  packages: write\n",
            "registry-url: https://npm.pkg.github.com",
            'scope: "@${{ github.repository_owner }}"',
            "npm ci",
            "npm test",
            "npm pack",
            "gh release create",
            "npm publish",
            "Refusing to invent a version.",
            'client-v${version}"',
        ):
            self.assertIn(part, text)
        self.assertNotIn("@rbe", text)
        self.assertNotIn("branches:", text)
        self.assertNotIn("make ", text.split("jobs:")[1])
        skill = (self.PIPELINE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "If the project has `client/package.json` and no"
            " `.github/workflows/publish-client.yml`, copy"
            " `templates/publish-client.yml` to that path.",
            skill,
        )
        files = (self.PIPELINE / "references" / "setup-files.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`templates/publish-client.yml`", files)
        contract = (self.PIPELINE / "references" / "contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`.github/workflows/publish-client.yml`", contract)

    def test_a_binary_runs_once_in_the_build_and_an_image_runs_with_smoke_args(self):
        """id: R-118"""
        go = (ROOT / "skills" / "r-go" / "templates" / "Makefile.golang").read_text(
            encoding="utf-8"
        )
        self.assertRegex(go, r"(?m)^BIN_SMOKE_ARGS \?= --help$")
        smoke = re.search(r"(?m)^BIN_SMOKE = (.+)$", go).group(1)
        self.assertIn("$(GO_RUN) build/$(BIN) $(BIN_SMOKE_ARGS)", smoke)
        self.assertIn("$(if $(or $(GOOS),$(GOARCH)),,", smoke)
        build = re.search(r"(?m)^BUILD_CMD = (.+)$", go).group(1)
        self.assertIn("-o build/$(BIN) $(BIN_PKG) $(BIN_SMOKE),", build)
        doc = (ROOT / "skills" / "r-go" / "references" / "build.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("runs `build/<name> $(BIN_SMOKE_ARGS)` in the Go image", doc)
        container = (self.PIPELINE / "container.mk").read_text(encoding="utf-8")
        self.assertIn('podman run --rm "$(CI_IMAGE)" $(SMOKE_ARGS)', container)
        image = (self.PIPELINE / "templates" / "Makefile.image").read_text(
            encoding="utf-8"
        )
        self.assertIn("# SMOKE_ARGS = --help", image)

    def test_the_web_smoke_check_looks_for_the_page_root_and_the_api_needle(self):
        """id: R-119"""
        node = (self.PIPELINE / "templates" / "Makefile.node").read_text(
            encoding="utf-8"
        )
        self.assertRegex(node, r'(?m)^SMOKE_PAGE_NEEDLE \?= id="root"$')
        self.assertRegex(node, r"(?m)^SMOKE_NEEDLE \?= ok$")
        smoke = node.split("\nSMOKE_CMD = ")[1].split("\n\n")[0]
        self.assertIn('"https://127.0.0.1:$(PORT)$(SMOKE_PATH)"', smoke)
        self.assertIn("grep -qF '$(SMOKE_NEEDLE)'", smoke)
        self.assertIn('"https://127.0.0.1:$(PORT)/"', smoke)
        self.assertIn("grep -qF '$(SMOKE_PAGE_NEEDLE)'", smoke)
        self.assertIn("[ -n '$(SMOKE_PAGE_NEEDLE)' ]", smoke)
        self.assertLess(
            smoke.index("SMOKE_PAGE_NEEDLE"), smoke.index('test "$$ok" = 1')
        )
        doc = (self.PIPELINE / "references" / "makefile.md").read_text(encoding="utf-8")
        self.assertIn("`SMOKE_PAGE_NEEDLE`", doc)

    def test_the_list_of_the_entry_file_row_is_the_one_list_of_the_skills(self):
        """id: R-16 R-60"""
        setup = (ROOT / "docs" / "requirements" / "project-setup.md").read_text(
            encoding="utf-8"
        )
        row = [line for line in setup.splitlines() if '<a id="r-60">' in line][0]
        sentence = row.split("The skills of the collection are ")[1].split(
            ". This list is the one list"
        )[0]
        listed = re.findall(r"`(r-[a-z-]+)`", sentence)
        self.assertEqual(len(listed), len(set(listed)))
        folders = sorted(path.name for path in (ROOT / "skills").glob("r-*"))
        self.assertEqual(sorted(listed), folders)
        collection = (ROOT / "docs" / "requirements" / "collection.md").read_text(
            encoding="utf-8"
        )
        row16 = [line for line in collection.splitlines() if '<a id="r-16">' in line][0]
        self.assertIn("[R-60](project-setup.md#r-60)", row16)
        self.assertEqual(re.findall(r"`(r-[a-z-]+)`", row16), [])

    def test_a_publish_job_runs_on_a_push_only_with_the_flag_and_always_on_dispatch(
        self,
    ):
        """id: R-121"""
        flag = (
            "(github.event_name == 'push' && github.ref =="
            " format('refs/heads/{0}', github.event.repository.default_branch)"
            " && vars.AUTO_PUBLISH == 'true') ||"
        )
        counts = {"ci.node.yml": 1, "ci.make.yml": 1, "ci.gradle.yml": 2}
        for name, count in counts.items():
            workflow = (self.PIPELINE / "templates" / name).read_text(encoding="utf-8")
            jobs = re.findall(
                r"(?ms)^  (publish-[a-z]+):\n(.*?)(?=^  [a-z-]+:\n)",
                workflow + "  x:\n",
            )
            self.assertEqual(len(jobs), count, name)
            for job, body in jobs:
                condition = body.split("    if: >-\n")[1].split("    runs-on:")[0]
                lines = [line.strip() for line in condition.splitlines()]
                self.assertEqual(
                    lines, [flag, f"inputs.job == '{job}'"], f"{name} {job}"
                )
                self.assertIn("needs: [build, test]", body)
        client = (self.PIPELINE / "templates" / "publish-client.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("branches:", client)
        self.assertNotIn("AUTO_PUBLISH", client)
        sdlc = PIPELINE_MK.read_text(encoding="utf-8")
        container = (self.PIPELINE / "container.mk").read_text(encoding="utf-8")
        self.assertNotIn("AUTO_PUBLISH", sdlc + container)
        ci = re.search(r"(?m)^SDLC_CI \?= (.+)$", sdlc).group(1)
        self.assertNotIn("publish", ci)
        for name in ("Makefile.node", "Makefile.gradle", "Makefile.image"):
            text = (self.PIPELINE / "templates" / name).read_text(encoding="utf-8")
            for line in re.findall(r"(?m)^SDLC_CI \??= (.+)$", text):
                self.assertNotIn("publish", line, name)
        skill = (self.PIPELINE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "- By default only a human publishes a large artifact, such as a"
            " container image, to a registry, with `workflow_dispatch`.",
            skill,
        )
        self.assertIn("`AUTO_PUBLISH` set to `true`", skill)
        for path in (
            self.PIPELINE / "references" / "workflow.md",
            self.PIPELINE / "references" / "contract.md",
            self.PIPELINE / "templates" / "pipeline-rules.md",
            ROOT / "skills" / "r-release" / "SKILL.md",
        ):
            self.assertIn("AUTO_PUBLISH", path.read_text(encoding="utf-8"), path.name)
        setup = ROOT / "skills" / "r-project-setup" / "templates" / "CLAUDE.md"
        self.assertNotIn(
            "with the merge into the default branch", setup.read_text(encoding="utf-8")
        )

    def test_jvm_tooling_counts_a_kotlin_build_file_as_present(self):
        """id: R-66"""
        gradle = (ROOT / "skills" / "r-jvm" / "jvm.mk").read_text(encoding="utf-8")
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
        for name in ("r-project-report/report.mk", "r-project-setup/contract.mk"):
            text = (ROOT / "skills" / name).read_text(encoding="utf-8")
            self.assertIn("> build/project-report.md.tmp ||", text, name)
            self.assertIn(
                "mv build/project-report.md.tmp build/project-report.md", text
            )

    def test_the_diff_base_falls_back_to_the_local_default_branch(self):
        """id: R-12"""
        base = "git merge-base HEAD $(DEFAULT_BRANCH) 2>/dev/null || git rev-parse"
        paths = list(ROOT.glob("skills/*/templates/Makefile.*"))
        paths.append(ROOT / "skills/r-project-setup/test-changed.mk")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "git merge-base" in text:
                self.assertIn(base, text, str(path))

    def test_make_finds_the_default_branch_without_an_override(self):
        """id: R-12"""
        text = (ROOT / "skills/r-project-setup/tools.mk").read_text(encoding="utf-8")
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


PIPELINE_MK = ROOT / "skills" / "r-github-pipeline" / "sdlc.mk"

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


FAKE_GIT = """\
case "$*" in
    "tag -l v[0-9]*") cat tags.txt ;;
    "rev-parse --abbrev-ref HEAD") cat branch.txt ;;
    "rev-parse HEAD") cat head.txt ;;
    "rev-parse -q --verify origin/main") cat tip.txt 2>/dev/null || exit 1 ;;
    *) exit 1 ;;
esac
"""


class CheckTagRecipeTest(unittest.TestCase):
    """Runs the real check-tag recipe of sdlc.mk in sh against a fake git."""

    def check(self, tag, tags=("v0.3.0", "v0.4.0"), branch="main", head="a1", tip="a1"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "bin" / "git").write_text(FAKE_GIT, encoding="utf-8")
            (root / "bin" / "git").chmod(0o755)
            (root / "tags.txt").write_text("".join(f"{t}\n" for t in tags))
            (root / "branch.txt").write_text(branch + "\n")
            (root / "head.txt").write_text(head + "\n")
            if tip:
                (root / "tip.txt").write_text(tip + "\n")
            shell = expand_make_recipe("check-tag", {"DEFAULT_BRANCH": "main"})
            environment = {"PATH": f"{root / 'bin'}:{os.environ['PATH']}"}
            if tag is not None:
                environment["TAG"] = tag
            return subprocess.run(
                ["sh", "-c", shell],
                cwd=tmp,
                env=environment,
                capture_output=True,
                text=True,
            )

    def test_a_new_newer_tag_at_the_tip_of_the_default_branch_passes(self):
        """id: R-120"""
        for tag in ("v0.5.0", "v0.4.1", "v1.0.0", "v0.10.0"):
            result = self.check(tag)
            self.assertEqual(result.returncode, 0, f"{tag} {result.stderr}")
        result = self.check("v0.1.0", tags=())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_bad_old_or_existing_tag_fails_and_names_the_reason(self):
        """id: R-120"""
        cases = (
            (None, "set TAG"),
            ("0.5.0", "is not vMAJOR.MINOR.PATCH"),
            ("v0.5", "is not vMAJOR.MINOR.PATCH"),
            ("v0.5.0-rc1", "is not vMAJOR.MINOR.PATCH"),
            ("v0.4.0", "exists"),
            ("v0.3.5", "is not newer than v0.4.0"),
        )
        for tag, reason in cases:
            result = self.check(tag)
            self.assertNotEqual(result.returncode, 0, f"{tag}")
            self.assertIn(reason, result.stderr, f"{tag}")
        # a pre-release tag does not count as the nearest tag
        result = self.check("v0.3.5", tags=("v0.3.0", "v0.4.0-rc1"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_tag_off_the_tip_of_the_default_branch_fails(self):
        """id: R-120"""
        for kwargs in (
            {"branch": "feature"},
            {"head": "b2"},
            {"tip": ""},
        ):
            result = self.check("v0.5.0", **kwargs)
            self.assertNotEqual(result.returncode, 0, str(kwargs))
            self.assertIn("check out the tip of main", result.stderr)

    def test_the_skill_and_the_reference_name_the_target(self):
        """id: R-120"""
        skill = (ROOT / "skills" / "r-github-pipeline" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "- Before a `v*` tag is pushed, `make check-tag TAG=vX.Y.Z` must pass:",
            skill,
        )
        sdlc = PIPELINE_MK.read_text(encoding="utf-8")
        self.assertIn(".PHONY: help version check-tag ci", sdlc)


FAKE_SCOPE_GIT = """\
case "$*" in
    "merge-base HEAD origin/main") cat merge-base.txt 2>/dev/null || exit 1 ;;
    "cat-file -e "*) grep -qx "${3%%^*}" known.txt ;;
    "diff --name-only "*" HEAD") cat files.txt ;;
    *) exit 1 ;;
esac
"""

FAKE_CI_STATUS = """\
printf '%s\\n' "$*" >> status.log
[ -f passed.txt ]
"""


class CiScopeRecipeTest(unittest.TestCase):
    """Runs the real ci-scope recipe of sdlc.mk in sh against a fake git."""

    BOARD = "docs/history/ docs/ROADMAP.md docs/proposals/"

    def scope(self, files, before="a1", event="push", passed=True, base=""):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            for name, text in (("git", FAKE_SCOPE_GIT), ("status", FAKE_CI_STATUS)):
                (root / "bin" / name).write_text(text, encoding="utf-8")
                (root / "bin" / name).chmod(0o755)
            (root / "files.txt").write_text("".join(f"{f}\n" for f in files))
            (root / "known.txt").write_text("a1\nm1\n")
            if base:
                (root / "merge-base.txt").write_text(base + "\n")
            if passed:
                (root / "passed.txt").write_text("")
            shell = expand_make_recipe(
                "ci-scope",
                {
                    "DEFAULT_BRANCH": "main",
                    "CI_BOARD_FILES": self.BOARD,
                    "THIS_MAKE": str(root / "bin" / "status"),
                },
            )
            output = root / "output.txt"
            environment = {
                "PATH": f"{root / 'bin'}:{os.environ['PATH']}",
                "CI_BEFORE": before,
                "GITHUB_EVENT_NAME": event,
                "GITHUB_OUTPUT": str(output),
            }
            result = subprocess.run(
                ["sh", "-c", shell],
                cwd=tmp,
                env=environment,
                capture_output=True,
                text=True,
            )
            written = output.read_text() if output.exists() else ""
            calls = (
                (root / "status.log").read_text()
                if (root / "status.log").exists()
                else ""
            )
            summary = (root / "build" / "summaries" / "ci-scope.md").read_text()
            return result, written, calls, summary

    def test_a_push_of_board_files_after_a_passed_run_skips(self):
        """id: R-123"""
        result, written, calls, summary = self.scope(
            ["docs/history/H-1.md", "docs/ROADMAP.md", "docs/proposals/P-1.md"]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(written, "board-only=true\n")
        self.assertEqual(calls, "--no-print-directory ci-status SHA=a1\n")
        self.assertIn("setup, build, and test skip", summary)

    def test_a_new_branch_compares_with_the_merge_base(self):
        """id: R-123"""
        result, written, calls, _summary = self.scope(
            ["docs/history/H-1.md"], before="0" * 40, base="m1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(written, "board-only=true\n")
        self.assertEqual(calls, "--no-print-directory ci-status SHA=m1\n")

    def test_every_other_push_runs_the_jobs_and_names_the_reason(self):
        """id: R-123"""
        board = ["docs/history/H-1.md"]
        cases = (
            ({"files": ["docs/history/H-1.md", "src/main.go"]}, "src/main.go"),
            ({"files": ["docs/ROADMAP.md.bak"]}, "docs/ROADMAP.md.bak"),
            ({"files": ["docs/adr/ADR-1.md"]}, "docs/adr/ADR-1.md"),
            ({"files": board, "passed": False}, "did not pass"),
            ({"files": board, "event": "workflow_dispatch"}, "workflow_dispatch"),
            ({"files": board, "before": "x9"}, "not in the clone"),
            ({"files": board, "before": ""}, "not in the clone"),
        )
        for kwargs, reason in cases:
            result, written, _calls, summary = self.scope(**kwargs)
            self.assertEqual(result.returncode, 0, f"{kwargs} {result.stderr}")
            self.assertEqual(written, "board-only=false\n", str(kwargs))
            self.assertIn("setup, build, and test run", summary, str(kwargs))
            self.assertIn(reason, summary, str(kwargs))

    def test_the_workflow_templates_skip_the_jobs_only_on_a_push(self):
        """id: R-123"""
        for name in ("ci.make.yml", "ci.node.yml", "ci.gradle.yml"):
            workflow = (ROOT / "skills/r-github-pipeline/templates" / name).read_text(
                encoding="utf-8"
            )
            setup = workflow.split("\n  setup:\n")[1].split("\n  build:\n")[0]
            self.assertIn("board-only: ${{ steps.scope.outputs.board-only }}", setup)
            self.assertIn("fetch-depth: 0", setup)
            self.assertIn("CI_BEFORE: ${{ github.event.before }}", setup)
            self.assertLess(
                setup.index("make cleanup-actions-artifacts"),
                setup.index("make ci-scope"),
            )
            self.assertIn(
                "- if: steps.scope.outputs.board-only != 'true'\n        run: make setup",
                setup,
            )
            for job in ("build", "test"):
                body = workflow.split(f"\n  {job}:\n")[1].split("\n\n")[0]
                self.assertIn(
                    "if: (github.event_name == 'push' &&"
                    " needs.setup.outputs.board-only != 'true') ||",
                    body,
                    f"{name} {job}",
                )


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


HELP_MK = ROOT / "skills" / "r-project-setup" / "help.mk"
HELP_ORDER = ["Gates", "Project", "Board", "Delivery", "Tools"]
HELP_GROUP_OF = {
    "setup": "Gates",
    "build": "Gates",
    "test": "Gates",
    "editorconfig": "Gates",
    "format": "Gates",
    "format-fix": "Gates",
    "lint": "Gates",
    "integration": "Gates",
    "coverage": "Gates",
    "docs": "Gates",
    "test-changed": "Gates",
    "check-docs": "Gates",
    "ci": "Gates",
    "project-report": "Board",
    "old-board": "Board",
    "old-board-delete": "Board",
    "board-numbers": "Board",
    "toon": "Board",
    "ids": "Board",
    "id": "Board",
    "id-raise": "Board",
    "req": "Board",
    "links": "Board",
    "links-check": "Board",
    "version": "Delivery",
    "check-tag": "Delivery",
    "publish-tags": "Delivery",
    "report": "Delivery",
    "login": "Delivery",
    "image": "Delivery",
    "image-ci": "Delivery",
    "publish-container": "Delivery",
    "publish-github": "Delivery",
    "ci-status": "Delivery",
    "ci-scope": "Delivery",
    "pull-request": "Delivery",
    "pull-request-merge": "Delivery",
    "cleanup-container-versions": "Delivery",
    "cleanup-github-releases": "Delivery",
    "cleanup-actions-artifacts": "Delivery",
    "help": "Tools",
    "py": "Tools",
    "doctor": "Tools",
    "podman-start": "Tools",
    "skills-install": "Tools",
    "skills-update": "Tools",
    "apm": "Tools",
    "gh-image": "Tools",
    "npm": "Tools",
    "node-tooling": "Tools",
    "python-tooling": "Tools",
    "go": "Tools",
    "go-tooling": "Tools",
    "wrapper": "Tools",
    "jvm-tooling": "Tools",
    "podman-socket": "Tools",
}
TARGET_WITH_HELP = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*):.*## ")


def included_makefiles(path, found=None):
    """`path` and the makefiles that it includes, in the order Make reads them."""
    found = [] if found is None else found
    if path in found:
        return found
    found.append(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"-?include (\S+)$", line)
        if not match:
            continue
        name = re.sub(r"\$\(\w+_DIR\)", str(path.parent) + "/", match.group(1))
        if name.startswith(".claude/skills/"):
            name = str(ROOT / "skills" / name[len(".claude/skills/") :])
        if "$(" not in name and Path(name).exists():
            included_makefiles(Path(name).resolve(), found)
    return found


def help_output(makefiles, docs="", login="", groups=None):
    """The group headings and the targets under them that `make help` prints.

    Make is not in the test image. This takes HELP_LIST from help.mk, expands
    it as Make does, and runs the awk command on the makefiles.
    """
    text = HELP_MK.read_text(encoding="utf-8")
    body = text.split("\nHELP_LIST ?= ")[1].split("\n\n")[0]
    body = re.sub(r"\\\n\s*", " ", body).replace("\\#", "#")
    values = {
        "RENDER_DOCS": docs,
        "PUBLISH_IMAGE": login,
        "HELP_GROUPS": groups
        or re.search(r"(?m)^HELP_GROUPS \?= (.+)$", text).group(1),
        "MAKEFILE_LIST": " ".join(str(path) for path in makefiles),
    }
    command = re.sub(
        r"\$\$|\$\((\w+)\)",
        lambda match: "$" if match.group(1) is None else values[match.group(1)],
        body,
    )
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    order = []
    rows = {}
    for line in result.stdout.splitlines():
        if line.startswith("  "):
            rows[order[-1]].append(line.split()[0])
        elif line.endswith(":"):
            order.append(line[:-1])
            rows[order[-1]] = []
        else:
            assert line == "", f"unexpected help line: {line!r}"
    return order, rows, result.stdout


def targets_with_group(path):
    """Each target with a help text in a makefile, and the group marker above it."""
    group = None
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# help-group: "):
            group = line[len("# help-group: ") :].strip()
            continue
        match = TARGET_WITH_HELP.match(line)
        if match:
            found.append((match.group(1), group))
    return found


class HelpGroupsTest(unittest.TestCase):
    """The groups of `make help`, from help.mk and the markers of the makefiles."""

    SETUP = ROOT / "skills" / "r-project-setup"
    PIPELINE = ROOT / "skills" / "r-github-pipeline"

    def product(self, tmp, contract):
        makefile = write(
            Path(tmp),
            "Makefile",
            f"include {contract}\n\ndeploy: ## Deploy the app\n",
        )
        return [makefile] + included_makefiles(contract)

    def test_help_prints_the_groups_in_a_fixed_order_with_each_target_in_its_group(
        self,
    ):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            files = self.product(tmp, self.PIPELINE / "sdlc.mk")
            order, rows, _output = help_output(files)
        self.assertEqual(order, HELP_ORDER)
        self.assertEqual(rows["Project"], ["deploy"])
        for group, expected in (
            (
                "Gates",
                "setup build test editorconfig format format-fix lint integration"
                " coverage test-changed check-docs ci",
            ),
            ("Board", "project-report old-board toon ids id req links"),
            (
                "Delivery",
                "version check-tag publish-tags report image image-ci"
                " publish-container ci-status ci-scope pull-request pull-request-merge"
                " cleanup-container-versions cleanup-github-releases"
                " cleanup-actions-artifacts",
            ),
            (
                "Tools",
                "help py doctor podman-start skills-install skills-update apm gh-image",
            ),
        ):
            self.assertEqual(
                sorted(set(expected.split()) - set(rows[group])), [], group
            )
        listed = [name for group in order for name in rows[group]]
        self.assertEqual(len(listed), len(set(listed)))

    def test_help_on_project_mk_has_no_delivery_group_until_an_image_is_published(
        self,
    ):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            files = self.product(tmp, self.SETUP / "project.mk")
            order, rows, _output = help_output(files)
            self.assertEqual(order, ["Gates", "Project", "Board", "Tools"])
            order, rows, _output = help_output(files, login="1")
            self.assertEqual(order, HELP_ORDER)
            self.assertEqual(rows["Delivery"], ["login"])

    def test_help_hides_docs_and_login_until_the_project_asks_for_them(self):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            files = self.product(tmp, self.PIPELINE / "sdlc.mk")
            _order, rows, _output = help_output(files)
            listed = [name for names in rows.values() for name in names]
            self.assertNotIn("docs", listed)
            self.assertNotIn("login", listed)
            self.assertIn("setup", listed)
            _order, rows, _output = help_output(files, docs="1", login="1")
            self.assertIn("docs", rows["Gates"])
            self.assertIn("login", rows["Delivery"])
            _order, rows, _output = help_output(files, docs="1")
            self.assertIn("docs", rows["Gates"])
            self.assertNotIn("login", rows["Delivery"])

    def test_a_group_outside_the_order_prints_after_the_named_groups(self):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            first = write(
                Path(tmp),
                "first.mk",
                "p: ## In project\n"
                "# help-group: Zeta\nz: ## In zeta\n"
                "# help-group: Gates\ng: ## Gate\n"
                "# help-group: Alpha\na: ## In alpha\n",
            )
            second = write(
                Path(tmp),
                "second.mk",
                "# help-group: Tools\ng: ## Second\nt: ## In tools\n",
            )
            order, rows, output = help_output(
                [first, second], groups="Gates Missing Tools"
            )
        self.assertEqual(order, ["Gates", "Tools", "Project", "Zeta", "Alpha"])
        self.assertEqual(rows["Gates"], ["g"])
        self.assertEqual(rows["Tools"], ["t"])
        self.assertIn("Gate", output)
        self.assertNotIn("Second", output)
        self.assertNotIn("Missing", output)

    def test_a_marker_applies_to_its_own_file_and_each_file_starts_in_project(self):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            first = write(Path(tmp), "first.mk", "# help-group: Tools\na: ## One\n")
            second = write(Path(tmp), "second.mk", "b: ## Two\n")
            order, rows, _output = help_output([first, second])
        self.assertEqual(order, ["Project", "Tools"])
        self.assertEqual(rows, {"Project": ["b"], "Tools": ["a"]})

    def test_a_group_marker_works_inside_a_hidden_block_and_endif_ends_the_hiding(
        self,
    ):
        """id: R-11"""
        with tempfile.TemporaryDirectory() as tmp:
            file = write(
                Path(tmp),
                "hidden.mk",
                "ifeq ($(RENDER_DOCS),1)\n# help-docs\n# help-group: Gates\n"
                "docs: ## Render\nendif\nafter: ## Shown\n",
            )
            order, rows, _output = help_output([file])
            self.assertEqual(rows, {"Gates": ["after"]})
            order, rows, _output = help_output([file], docs="1")
            self.assertEqual(rows, {"Gates": ["docs", "after"]})

    def test_project_mk_and_sdlc_mk_run_the_one_list_from_help_mk(self):
        """id: R-11"""
        project = (self.SETUP / "project.mk").read_text(encoding="utf-8")
        sdlc = (self.PIPELINE / "sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("\ninclude $(PROJECT_MK_DIR)help.mk\n", project)
        self.assertIn("\ninclude $(SDLC_MK_DIR)../r-project-setup/help.mk\n", sdlc)
        for name, text in (("project.mk", project), ("sdlc.mk", sdlc)):
            recipe = text.split("\nhelp: ## ")[1].split("\n\n")[0]
            self.assertIn("\t@$(HELP_LIST)", recipe, name)
            self.assertNotIn("awk", recipe, name)
            self.assertIn("@printf '%s\\n' \"$(HELP_LEAD)\"", recipe, name)
        self.assertIn(
            "make ci runs $(SDLC_CI). It does not publish.",
            sdlc.split("\nhelp: ## ")[1].split("\n\n")[0],
        )
        help_mk = HELP_MK.read_text(encoding="utf-8")
        self.assertIn("\nifndef HELP_MK\nHELP_MK := 1\n", help_mk)
        self.assertIn("\nHELP_GROUPS ?= Gates Project Board Delivery Tools\n", help_mk)
        self.assertTrue(help_mk.endswith(".DEFAULT_GOAL := help\n\nendif\n"))

    def test_the_help_command_uses_posix_awk_only(self):
        """id: R-11"""
        help_mk = HELP_MK.read_text(encoding="utf-8")
        body = help_mk.split("\nHELP_LIST ?= ")[1].split("\n\n")[0]
        self.assertTrue(body.startswith("awk "))
        self.assertNotRegex(
            body,
            r"\b(asort|asorti|gensub|strftime|systime|PROCINFO|BEGINFILE|ENDFILE"
            r"|IGNORECASE|FPAT|patsplit|switch|length\()",
        )
        self.assertNotIn("'", body.split("'", 1)[1].rsplit("'", 1)[0])

    def test_every_target_with_a_help_text_sits_under_the_group_marker_of_its_group(
        self,
    ):
        """id: R-11"""
        files = [
            path
            for path in sorted((ROOT / "skills").glob("*/*.mk"))
            if path.name != "help.mk"
        ]
        self.assertGreater(len(files), 15)
        found = 0
        for path in files:
            for target, group in targets_with_group(path):
                found += 1
                self.assertIsNotNone(group, f"{path.name}: {target} has no marker")
                self.assertIn(group, HELP_ORDER, f"{path.name}: {target}")
                expected = HELP_GROUP_OF.get(target)
                self.assertEqual(group, expected, f"{path.name}: {target}")
        self.assertGreater(found, 45)


LANGUAGE_FILES = {
    "r-node/node.mk": {
        "targets": ["npm", "node-tooling"],
        "variables": ["NODE", "NODE_IMAGE", "NODE_VERSION", "NODE_DEV_TOOLS"],
    },
    "r-python/python.mk": {"targets": ["python-tooling"], "variables": []},
    "r-go/go.mk": {
        "targets": ["go", "go-tooling"],
        "variables": ["GO_IMAGE", "GO_CACHE", "GO_OPTS", "GO_RUN", "GO", "MODULE"],
    },
    "r-jvm/jvm.mk": {
        "targets": ["wrapper", "jvm-tooling", "podman-socket"],
        "variables": [
            "JDK_IMAGE",
            "GRADLE_VERSION",
            "GRADLE_IMAGE",
            "GRADLE_RUN",
            "PODMAN_SOCKET",
        ],
    },
}
LANGUAGE_TEMPLATES = (
    ("r-node/templates/Makefile.node", "r-node/node.mk", "r-project-setup/project.mk"),
    (
        "r-python/templates/Makefile.python",
        "r-python/python.mk",
        "r-project-setup/project.mk",
    ),
    ("r-go/templates/Makefile.golang", "r-go/go.mk", "r-project-setup/project.mk"),
    ("r-jvm/templates/Makefile.gradle", "r-jvm/jvm.mk", "r-project-setup/project.mk"),
    (
        "r-github-pipeline/templates/Makefile.node",
        "r-node/node.mk",
        "r-github-pipeline/sdlc.mk",
    ),
    (
        "r-github-pipeline/templates/Makefile.gradle",
        "r-jvm/jvm.mk",
        "r-github-pipeline/sdlc.mk",
    ),
)


class LanguageIncludeFileTest(unittest.TestCase):
    """The include file of each language skill holds the targets of its language."""

    def read(self, relative):
        return (ROOT / "skills" / relative).read_text(encoding="utf-8")

    def test_a_language_template_includes_its_file_and_defines_none_of_its_targets(
        self,
    ):
        """id: R-122"""
        for template, language, contract in LANGUAGE_TEMPLATES:
            text = self.read(template)
            spec = LANGUAGE_FILES[language]
            include = f"\ninclude .claude/skills/{language}\n"
            self.assertEqual(text.count(include), 1, template)
            self.assertGreater(
                text.index(include),
                text.index(f"\ninclude .claude/skills/{contract}\n"),
                template,
            )
            for target in spec["targets"]:
                self.assertNotRegex(text, rf"(?m)^{target}:", f"{template} {target}")
                self.assertNotRegex(
                    text, rf"(?m)^\.PHONY: {target}$", f"{template} {target}"
                )
            self.assertNotRegex(text, r"(?m)^PODMAN_SOCKET", template)
            if "github-pipeline" not in template:
                for variable in spec["variables"]:
                    self.assertNotRegex(
                        text, rf"(?m)^{variable} \??= ", f"{template} {variable}"
                    )

    def test_the_go_template_keeps_the_run_target_of_the_project(self):
        """id: R-122"""
        text = self.read("r-go/templates/Makefile.golang")
        self.assertRegex(text, r"(?m)^run: ## ")
        self.assertRegex(text, r"(?m)^ARGS \?=$")

    def test_the_pipeline_node_template_gives_node_mk_the_image_it_needs(self):
        """id: R-122"""
        template = self.read("r-github-pipeline/templates/Makefile.node")
        node = self.read("r-node/node.mk")
        self.assertRegex(node, r"(?m)^NODE \?= podman run .*\\$")
        self.assertIn("$(NODE_IMAGE)", node.split("\nNODE ?= ")[1].split("\n\n")[0])
        self.assertLess(
            template.index("\nNODE_IMAGE ?= "),
            template.index("\ninclude .claude/skills/r-node/node.mk\n"),
        )

    def test_a_language_file_defines_its_targets_and_its_defaults_with_the_marker(
        self,
    ):
        """id: R-122"""
        for language, spec in LANGUAGE_FILES.items():
            text = self.read(language)
            guard = re.search(r"(?m)^ifndef (\w+_MK)\n\1 := 1$", text)
            self.assertIsNotNone(guard, language)
            phony = " ".join(re.findall(r"(?m)^\.PHONY:(.*)$", text)).split()
            found = targets_with_group(ROOT / "skills" / language)
            self.assertEqual([name for name, _ in found], spec["targets"], language)
            for target, group in found:
                self.assertEqual(group, "Tools", f"{language} {target}")
                self.assertIn(target, phony, f"{language} {target}")
            for variable in spec["variables"]:
                self.assertRegex(
                    text, rf"(?m)^{variable} \?= ", f"{language} {variable}"
                )
                self.assertNotRegex(
                    text, rf"(?m)^{variable} = ", f"{language} {variable}"
                )
            self.assertTrue(text.endswith(".DEFAULT_GOAL := help\n\nendif\n"), language)

    def test_the_gradle_defaults_match_the_template_values_they_replaced(self):
        """id: R-122"""
        jvm = self.read("r-jvm/jvm.mk")
        for line in (
            "JDK_IMAGE ?= docker.io/library/eclipse-temurin:25-jdk",
            "GRADLE_VERSION ?= 9.1.0",
            "GRADLE_IMAGE ?= docker.io/library/gradle:$(GRADLE_VERSION)-jdk25",
            "PODMAN_SOCKET ?= $$(podman info --format '{{.Host.RemoteSocket.Path}}')",
        ):
            self.assertIn("\n" + line + "\n", jvm)
        node = self.read("r-node/node.mk")
        self.assertIn("\nNODE_VERSION ?= 24\n", node)
        self.assertIn(
            "\nNODE_IMAGE ?= docker.io/library/node:$(NODE_VERSION)-bookworm-slim\n",
            node,
        )
        go = self.read("r-go/go.mk")
        self.assertIn("\nGO_IMAGE ?= docker.io/library/golang:1.25-bookworm\n", go)
        self.assertIn("\nGO ?= $(GO_RUN) go\n", go)

    def test_podman_socket_checks_the_socket_in_the_mount_namespace_of_rootless_podman(
        self,
    ):
        """id: R-122"""
        jvm = self.read("r-jvm/jvm.mk")
        recipe = jvm.split("\npodman-socket: ## ")[1].split("\n\n")[0]
        for part in (
            "{{.Host.ServiceIsRemote}}",
            "systemctl --user start podman.socket",
            "podman system service --time=0",
            'podman unshare test -S "$$sock"',
            "podman system migrate",
        ):
            self.assertIn(part, recipe)
        self.assertEqual(recipe.count('podman unshare test -S "$$sock"'), 2)
        self.assertEqual(recipe.count("podman system migrate"), 2)

    def test_the_root_makefile_of_the_collection_includes_no_language_file(self):
        """id: R-122"""
        text = (ROOT / "Makefile").read_text(encoding="utf-8")
        for language in LANGUAGE_FILES:
            self.assertNotIn(language, text)

    def test_a_language_skill_names_its_include_file(self):
        """id: R-122"""
        for language in LANGUAGE_FILES:
            skill, name = language.split("/")
            text = self.read(f"{skill}/SKILL.md")
            self.assertIn(f"`{name}`", text, skill)
            tooling = self.read(f"{skill}/references/tooling.md")
            self.assertIn(f"include .claude/skills/{language}", tooling, skill)


if __name__ == "__main__":
    unittest.main()
