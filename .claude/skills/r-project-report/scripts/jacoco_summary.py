#!/usr/bin/env python3
"""Write build/summaries/coverage.md from the JaCoCo XML report of Gradle.

JacocoReport writes jacocoTestReport.xml under build/reports/jacoco. A
file named jacoco.xml is not that report. The report job of
r-github-pipeline reads build/summaries/.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPORTS = Path("build/reports/jacoco")
SUMMARY = Path("build/summaries/coverage.md")
COUNTERS = ("INSTRUCTION", "LINE", "BRANCH", "METHOD")


def integer(value):
    try:
        return int(value or 0)
    except ValueError:
        return 0


def percent(covered, missed):
    total = covered + missed
    if total == 0:
        return "n/a"
    return "%.1f%%" % (100.0 * covered / total)


def summary_lines(report: ET.Element) -> list[str]:
    lines = ["# Coverage", ""]
    for counter in report.findall("counter"):
        kind = counter.attrib.get("type", "")
        if kind not in COUNTERS:
            continue
        covered = integer(counter.attrib.get("covered"))
        missed = integer(counter.attrib.get("missed"))
        lines.append(
            f"- {kind.title()}: {percent(covered, missed)} ({covered} covered, {missed} missed)"
        )
    lines.append("")
    return lines


def write_summary(root: Path) -> None:
    reports = root / REPORTS
    summary = root / SUMMARY
    matches = sorted(reports.rglob("jacocoTestReport.xml")) if reports.is_dir() else []
    if not matches:
        summary.unlink(missing_ok=True)
        return
    summary.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = ET.parse(matches[0]).getroot()
    except ET.ParseError as exc:
        summary.write_text(
            f"# Coverage\n\nJaCoCo XML could not be parsed: {exc}\n", encoding="utf-8"
        )
        return
    summary.write_text("\n".join(summary_lines(report)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_summary(Path.cwd())
    sys.exit(0)
