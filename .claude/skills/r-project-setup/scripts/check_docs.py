#!/usr/bin/env python3
"""Fail when a skill text names a path or a Make target that does not exist.

A SKILL.md and a reference file of an installed skill may name a path
under skills/r-<name>/ or .claude/skills/r-<name>/, and a `make <target>`.
This check reads the text and the makefiles of the repository, and it
prints each name that points to nothing.
"""

import os
import re
import sys
from pathlib import Path

PATH_PATTERN = re.compile(
    r"(?<![\w/.-])((?:\.claude/)?skills/r-[a-z0-9][a-z0-9-]*(?:/[^\s`'\")\]>,;:|]+)*)"
)
CODE_PATTERN = re.compile(r"`([^`\n]+)`")
TARGET_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
DEFINITION_PATTERN = re.compile(r"^([^\s#:=$%(][^:=#]*?)\s*:(?![=:])")
SKIPPED_DIRECTORIES = {".git", "build", "node_modules", "apm_modules"}
PLACEHOLDER_CHARACTERS = "<*{[$"


def skill_directory(root):
    installed = root / ".claude" / "skills"
    if installed.is_dir() and any(installed.glob("*/SKILL.md")):
        return installed
    return root / "skills"


def text_files(directory):
    found = []
    for skill in sorted(directory.glob("*/")):
        if (skill / "SKILL.md").is_file():
            found.append(skill / "SKILL.md")
            found.extend(sorted((skill / "references").glob("**/*.md")))
    return found


def makefiles(root):
    found = []
    for current, directories, names in os.walk(root):
        directories[:] = [d for d in directories if d not in SKIPPED_DIRECTORIES]
        for name in names:
            if name.startswith("Makefile") or name.endswith(".mk"):
                found.append(Path(current) / name)
    return found


def defined_targets(root):
    targets = set()
    for path in makefiles(root):
        continued = False
        for line in path.read_text(encoding="utf-8").splitlines():
            was_continued = continued
            continued = line.endswith("\\")
            if was_continued or line.startswith("\t"):
                continue
            match = DEFINITION_PATTERN.match(line)
            if not match:
                continue
            targets.update(
                word
                for word in match.group(1).split()
                if word != ".PHONY" and NAME_PATTERN.match(word)
            )
    return targets


def named_paths(text):
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in PATH_PATTERN.finditer(line):
            following = line[match.end() : match.end() + 1]
            name = match.group(1).rstrip(".")
            if following and following in PLACEHOLDER_CHARACTERS:
                continue
            if any(character in name for character in PLACEHOLDER_CHARACTERS):
                continue
            found.append((number, name))
    return found


def command_targets(command):
    words = command.split()
    if not words or words[0] != "make":
        return []
    targets = []
    skip = False
    for word in words[1:]:
        if skip:
            skip = False
        elif word == "-f":
            skip = True
        elif word.startswith("-"):
            continue
        elif "=" in word:
            break
        elif TARGET_PATTERN.match(word):
            targets.append(word)
        else:
            break
    return targets


def named_targets(text):
    found = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        commands = [line.strip()] if fenced else CODE_PATTERN.findall(line)
        for command in commands:
            for target in command_targets(command):
                found.append((number, target))
    return found


def path_exists(root, name, strict):
    relative = name.removeprefix(".claude/")
    candidates = [root / name, root / ".claude" / relative, root / relative]
    if any(candidate.exists() for candidate in candidates):
        return True
    skill = relative.split("/")[1]
    present = any(
        (base / skill).is_dir()
        for base in (root / ".claude" / "skills", root / "skills")
    )
    return not strict and not present


def problems(root):
    directory = skill_directory(root)
    strict = directory == root / "skills"
    targets = defined_targets(root)
    errors = []
    for path in text_files(directory):
        shown = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        for number, name in named_paths(text):
            if not path_exists(root, name, strict):
                errors.append(f"{shown}:{number}: the path {name} does not exist")
        for number, target in named_targets(text):
            if target not in targets:
                errors.append(f"{shown}:{number}: no makefile defines make {target}")
    return errors


def main():
    errors = problems(Path.cwd())
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print("check-docs: no skill text names a missing path or a missing target")
    return 1 if errors else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
