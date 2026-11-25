#!/usr/bin/env python3
"""Write the project report. Hand-editing the file is a defect."""

import importlib.util
import sys
from pathlib import Path

# Each check is a skill, the tag that holds its numbered steps, and the
# heading that held them before the skills used tags.
ARCHITECTURE_CHECKS = (("plan", "steps", "## Work"), ("review", "steps", "## Work"))
DEVELOPMENT_CHECKS = (
    ("develop", "steps", "## Work"),
    ("review", "steps", "## Work"),
    ("release", "steps", "## Work"),
    ("project-setup", "checks", "## Quality targets"),
)


def sibling(name: str):
    loaded = sys.modules.get(f"_project_report_{name}")
    if loaded is not None:
        return loaded
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_project_report_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    if spec.loader is None:
        raise ImportError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def skill_text(root: Path, name: str) -> str | None:
    for base in (root / ".claude" / "skills", root / "skills"):
        path = base / name / "SKILL.md"
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def block_lines(text: str, tag: str, heading: str) -> list[str]:
    """The lines of the first `<tag>` block, or else the lines under the heading.

    The opening tag and the closing tag are each alone on a line.
    """
    lines = text.splitlines()
    stripped = [line.strip() for line in lines]
    if f"<{tag}>" in stripped:
        start = stripped.index(f"<{tag}>") + 1
        end = start
        while end < len(lines) and stripped[end] != f"</{tag}>":
            end += 1
        return lines[start:end]
    if heading in stripped:
        start = stripped.index(heading) + 1
        end = start
        while end < len(lines) and not lines[end].startswith("#"):
            end += 1
        return lines[start:end]
    return []


def numbered_steps(text: str, tag: str, heading: str) -> list[str]:
    steps = []
    current = ""
    for line in block_lines(text, tag, heading):
        match_indent = line.startswith((" ", "\t"))
        numbered = line[:1].isdigit() and ". " in line[:4]
        if numbered and not match_indent:
            if current:
                steps.append(current)
            current = line.strip()
            continue
        if current and match_indent and line.strip():
            current = f"{current} {line.strip()}"
            continue
        if current and not line.strip():
            steps.append(current)
            current = ""
    if current:
        steps.append(current)
    return steps


def cell(text: str) -> str:
    return text.replace("|", "/")


def tests_for(requirement_id: str, proofs_found) -> list[str]:
    return sorted(
        {
            proof.qualified_name
            for proof in proofs_found
            if proof.requirement_id == requirement_id
        }
    )


def superseded(item) -> bool:
    return item.kind == "adr" and item.status.strip().lower() == "superseded"


def linker(requirements, extra=()):
    """A function that links the known ids in a text."""
    known = {ident: "" for ident in extra}
    known.update({item.id: item.path for item in requirements})
    module = sibling("report_links")
    return lambda text: module.link_text(text, known)


def format_requirement(item, proofs_found, link) -> str:
    proved = tests_for(item.id, proofs_found)
    names = "; ".join(proved) if proved else "no test"
    status = item.status or "unspecified"
    title = link((item.title or item.id).rstrip("."))
    ident = sibling("report_links").link(item.id, item.path)
    if item.kind == "planned":
        return f"- {ident}, planned. {title}."
    if item.kind not in sibling("requirements").PROVABLE:
        return f"- {ident}, {status}, {item.kind}. {title}."
    return f"- {ident}, {status}, {item.kind}. {title}. Proved by: {names}."


def append_requirements(lines: list[str], items, proofs_found, kind: str, link) -> None:
    chosen = [item for item in items if item.kind == kind]
    if not chosen:
        lines.append("None.")
        lines.append("")
        return
    for item in chosen:
        lines.append(format_requirement(item, proofs_found, link))
    lines.append("")


def append_lines(lines: list[str], entries: list[str], link=str) -> None:
    if not entries:
        lines.append("None.")
    else:
        for entry in entries:
            lines.append(f"- {link(entry)}")
    lines.append("")


def append_checks(lines: list[str], root: Path, checks) -> None:
    for name, tag, heading in checks:
        lines.append(f"#### {name}")
        lines.append("")
        text = skill_text(root, name)
        if text is None:
            lines.append(f"{name}: not installed")
            lines.append("")
            continue
        steps = numbered_steps(text, tag, heading)
        if not steps:
            lines.append("None.")
        else:
            for step in steps:
                lines.append(f"- {step}")
        lines.append("")


def append_proof_map(lines: list[str], requirements, proofs_found) -> None:
    ident_link = sibling("report_links").link
    provable = sibling("requirements").PROVABLE
    requirements = [item for item in requirements if item.kind in provable]
    lines.append("| Id | Kind | Status | Tests |")
    lines.append("| --- | --- | --- | --- |")
    for item in requirements:
        proved = tests_for(item.id, proofs_found)
        names = "; ".join(proved) if proved else "no test"
        lines.append(
            f"| {cell(ident_link(item.id, item.path))} | {cell(item.kind)} | {cell(item.status)} | {cell(names)} |"
        )
    lines.append("")
    lines.append("### Ids with no test")
    lines.append("")
    gaps = [
        item
        for item in requirements
        if not superseded(item) and not tests_for(item.id, proofs_found)
    ]
    if not gaps:
        lines.append("None.")
    else:
        for item in gaps:
            lines.append(f"- {ident_link(item.id, item.path)} ({item.kind})")
    lines.append("")
    lines.append("### Tests with no id")
    lines.append("")
    missing = [
        proof.qualified_name for proof in proofs_found if proof.requirement_id is None
    ]
    append_lines(lines, missing)
    lines.append("### Tests whose id is not a requirement")
    lines.append("")
    known = {item.id for item in requirements}
    unknown = [
        f"{proof.qualified_name} names {proof.requirement_id}"
        for proof in proofs_found
        if proof.requirement_id is not None and proof.requirement_id not in known
    ]
    append_lines(lines, unknown)


def render_product(root: Path, requirements, proofs_found) -> str:
    link = linker(requirements)
    lines = [
        "# Project report",
        "",
        "Generated by `make project-report`. Hand-editing this file is a defect.",
        "",
        "## Requirements",
        "",
        "The id is an ADR id or a row of a file in `docs/requirements/`. A roadmap row is work, not a rule.",
        "The test names that id with `id:` in its header or metadata.",
        "",
    ]
    append_proof_map(lines, requirements, proofs_found)
    lines.append("## Architecture review")
    lines.append("")
    lines.append(
        "Drawn from the ADRs, the roadmap, and the checks in `plan` and `review`."
    )
    lines.append("")
    lines.append("### ADRs")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "adr", link)
    lines.append("### Roadmap")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "roadmap", link)
    lines.append("### Checks")
    lines.append("")
    append_checks(lines, root, ARCHITECTURE_CHECKS)
    lines.append("## Development review")
    lines.append("")
    lines.append(
        "Drawn from the ADRs, the roadmap, the planned requirements, "
        "and the checks in `develop`, `review`, `release`, and `project-setup`."
    )
    lines.append("")
    lines.append("### ADRs")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "adr", link)
    lines.append("### Roadmap")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "roadmap", link)
    lines.append("### Planned requirements")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "planned", link)
    lines.append("### Checks")
    lines.append("")
    append_checks(lines, root, DEVELOPMENT_CHECKS)
    return "\n".join(lines).rstrip() + "\n"


def render_requirements_list(root: Path, requirements, proofs_found) -> str:
    link = linker(requirements)
    lines = [
        "# Project report",
        "",
        "Generated by `make project-report`. Hand-editing this file is a defect.",
        "",
        "## Requirements",
        "",
        "The id is a row in a file in `docs/requirements/`. A planned row is open work, not a rule in force.",
        "The test names that id with `id:` in its header or metadata.",
        "",
    ]
    ident_link = sibling("report_links").link
    for item in requirements:
        lines.append(f"- {ident_link(item.id, item.path)}. {link(item.title)}")
    lines.append("")
    append_proof_map(lines, requirements, proofs_found)
    lines.append("## Architecture review")
    lines.append("")
    lines.append(
        "This collection has no ADR directory and no roadmap. "
        "The checks in `plan` and `review` still apply."
    )
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    append_checks(lines, root, ARCHITECTURE_CHECKS)
    lines.append("## Development review")
    lines.append("")
    lines.append(
        "The open work of this collection is the planned rows of the files in `docs/requirements/`. "
        "The checks in `develop`, `review`, `release`, and `project-setup` still apply."
    )
    lines.append("")
    lines.append("### Planned requirements")
    lines.append("")
    append_requirements(lines, requirements, proofs_found, "planned", link)
    lines.append("### Checks")
    lines.append("")
    append_checks(lines, root, DEVELOPMENT_CHECKS)
    return "\n".join(lines).rstrip() + "\n"


def render(root: Path, requirements, proofs_found) -> str:
    requirements_module = sibling("requirements")
    if requirements_module.uses_requirements_list(root):
        return render_requirements_list(root, requirements, proofs_found)
    return render_product(root, requirements, proofs_found)


def build(root: Path) -> tuple[str, list[str]]:
    requirements_module = sibling("requirements")
    requirements = requirements_module.collect(root)
    proofs_found = requirements_module.proofs(root)
    text = render(root, requirements, proofs_found)
    return text, requirements_module.problems(requirements, proofs_found)


def main() -> int:
    requirements_module = sibling("requirements")
    root = requirements_module.repo_root(Path.cwd())
    text, errors = build(root)
    sys.stdout.write(text)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
