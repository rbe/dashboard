#!/usr/bin/env python3
"""The check-docs script: a skill text names a path or a target that exists."""

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

spec = importlib.util.spec_from_file_location("check_docs", HERE / "check_docs.py")
check_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_docs)


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def product(root, skill_text, makefile=""):
    """A product repository with two installed skills and one Makefile."""
    write(root, ".claude/skills/r-alpha/SKILL.md", skill_text)
    write(root, ".claude/skills/r-alpha/index.mk", "toon:\n\techo toon\n")
    write(root, ".claude/skills/r-beta/SKILL.md", "---\nname: r-beta\n---\n")
    write(root, "Makefile", makefile)


class CheckDocsTest(unittest.TestCase):
    def errors(self, skill_text, makefile=""):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product(root, skill_text, makefile)
            return check_docs.problems(root)

    def test_a_path_that_exists_passes(self):
        """id: R-111"""
        text = "Read `.claude/skills/r-alpha/index.mk` and skills/r-alpha/index.mk."
        self.assertEqual(self.errors(text), [])

    def test_a_path_to_a_missing_file_of_an_installed_skill_fails(self):
        """id: R-111"""
        errors = self.errors("Run `.claude/skills/r-alpha/gone.mk`.\n")
        self.assertEqual(
            errors,
            [
                ".claude/skills/r-alpha/SKILL.md:1: "
                "the path .claude/skills/r-alpha/gone.mk does not exist"
            ],
        )

    def test_a_trailing_dot_and_a_placeholder_are_not_part_of_a_path(self):
        """id: R-111"""
        text = (
            "See .claude/skills/r-alpha/index.mk.\n"
            "The skills/r-upgrade-<language>-components and skills/r-*/ stay.\n"
            "Also skills/r-alpha/<file>.md stays.\n"
        )
        self.assertEqual(self.errors(text), [])

    def test_a_path_in_a_reference_file_is_checked(self):
        """id: R-111"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product(root, "")
            write(
                root,
                ".claude/skills/r-alpha/references/a.md",
                "x\nSee skills/r-alpha/missing.md here.\n",
            )
            errors = check_docs.problems(root)
        self.assertEqual(len(errors), 1)
        self.assertIn(
            "references/a.md:2: the path skills/r-alpha/missing.md", errors[0]
        )

    def test_a_skill_that_is_not_installed_is_no_drift_in_a_product(self):
        """id: R-111"""
        self.assertEqual(self.errors("See .claude/skills/r-gamma/x.mk.\n"), [])

    def test_a_skill_that_is_missing_is_drift_in_the_collection(self):
        """id: R-111"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "skills/r-alpha/SKILL.md", "See skills/r-gamma/x.mk.\n")
            errors = check_docs.problems(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("skills/r-gamma/x.mk does not exist", errors[0])

    def test_a_target_that_a_makefile_defines_passes(self):
        """id: R-111"""
        text = (
            "Run `make -s toon`, `make build ARGS=x`, `make -f a.mk lint`,\n"
            "`make <target>`, and `make id KIND=R`.\n```\nmake test\n```\n"
        )
        makefile = (
            ".PHONY: build\nbuild: ## x\n\techo build\n"
            "VAR := a:b\nid:\n\techo id\nlint test:\n\techo\n"
        )
        self.assertEqual(self.errors(text, makefile), [])

    def test_a_target_that_no_makefile_defines_fails(self):
        """id: R-111"""
        errors = self.errors("Run `make ghost` now.\n", "build:\n\techo\n")
        self.assertEqual(
            errors,
            [".claude/skills/r-alpha/SKILL.md:1: no makefile defines make ghost"],
        )

    def test_a_target_in_a_fenced_block_is_checked(self):
        """id: R-111"""
        errors = self.errors("```\nmake ghost\n```\n")
        self.assertEqual(len(errors), 1)
        self.assertIn(":2: no makefile defines make ghost", errors[0])

    def test_a_recipe_line_does_not_define_a_target(self):
        """id: R-111"""
        makefile = "build:\n\tghost: not a target\nrun: x \\\n  y: z\n"
        errors = self.errors("`make ghost` `make y`\n", makefile)
        self.assertEqual(len(errors), 2)

    def test_prose_outside_code_names_no_target(self):
        """id: R-111"""
        self.assertEqual(self.errors("Make sure that make ghost is prose.\n"), [])

    def test_main_prints_each_problem_and_fails(self):
        """id: R-111"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product(root, "Run `make ghost`.\n")
            here = Path.cwd()
            out, err = io.StringIO(), io.StringIO()
            os.chdir(root)
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    failed = check_docs.main()
                product(root, "Run `make toon`.\n", "toon:\n\techo\n")
                with redirect_stdout(out), redirect_stderr(err):
                    passed = check_docs.main()
            finally:
                os.chdir(here)
        self.assertEqual(failed, 1)
        self.assertIn("no makefile defines make ghost", err.getvalue())
        self.assertEqual(passed, 0)
        self.assertIn("check-docs: no skill text names", out.getvalue())

    def test_a_target_of_a_skill_that_is_not_installed_is_not_missing(self):
        """id: R-111"""
        text = "Run `make ci-status` and `make wrapper`.\n"
        self.assertEqual(self.errors(text), [])

    def test_a_target_of_an_installed_optional_skill_must_exist(self):
        """id: R-111"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product(root, "Run `make ci-status`.\n")
            write(root, ".claude/skills/r-github-pipeline/SKILL.md", "x\n")
            errors = check_docs.problems(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("no makefile defines make ci-status", errors[0])

    def test_the_optional_target_table_matches_the_makefiles_of_the_collection(self):
        """id: R-111"""
        for skill, names in check_docs.OPTIONAL_SKILL_TARGETS.items():
            defined = check_docs.defined_targets(ROOT / "skills" / skill)
            self.assertEqual(sorted(names - defined), [], skill)

    def test_the_skills_of_this_collection_name_no_missing_path_or_target(self):
        """id: R-111"""
        self.assertEqual(check_docs.problems(ROOT), [])

    def test_the_makefiles_run_check_docs_before_the_tests(self):
        """id: R-111"""
        text = (ROOT / "skills/r-project-setup/check-docs.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("\ncheck-docs: ##", text)
        self.assertIn("\ntest: check-docs\n", text)
        project = (ROOT / "skills/r-project-setup/project.mk").read_text(
            encoding="utf-8"
        )
        self.assertIn("check-docs.mk", project)
        sdlc = (ROOT / "skills/r-github-pipeline/sdlc.mk").read_text(encoding="utf-8")
        self.assertIn("include $(SDLC_MK_DIR)../r-project-setup/project.mk", sdlc)

    def test_a_language_target_is_named_only_by_its_language_skills(self):
        """id: R-111"""
        owners = {
            "r-node": ("npm", "node-tooling"),
            "r-python": ("python-tooling",),
            "r-go": ("go", "go-tooling"),
            "r-jvm": ("wrapper", "jvm-tooling", "podman-socket"),
        }
        found = []
        for path in sorted((ROOT / "skills").glob("r-*/**/*.md")):
            skill = path.relative_to(ROOT / "skills").parts[0]
            text = path.read_text(encoding="utf-8")
            for owner, targets in owners.items():
                if skill == owner:
                    continue
                for target in targets:
                    if f"`make {target}`" in text or f"`make {target} " in text:
                        found.append(f"{path.relative_to(ROOT)}: make {target}")
        self.assertEqual(found, [])
