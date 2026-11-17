"""Annotate failed GitHub Actions jobs and retain complete pytest failure detail.

Runs *after* a failed step. Never intercepts pytest stdout/stderr or alters
the original test process exit status. Success paths do not invoke this script.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from xml.etree import ElementTree as ET


def _escape_annotation(value: str) -> str:
    """Escape workflow-command delimiters in values originating in test output."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def summarize(junit: Path, label: str, environment: dict[str, str]) -> tuple[list[str], str]:
    lines = [f"### {label}: failed", "",
             f"Commit: `{environment.get('GITHUB_SHA', 'unknown')}`",
             f"Runner: `{environment.get('RUNNER_OS', 'unknown')}`",
             f"Job: `{environment.get('GITHUB_JOB', 'unknown')}`"]
    repo = environment.get("GITHUB_REPOSITORY", "")
    run = environment.get("GITHUB_RUN_ID", "")
    if repo and run:
        lines.append(f"Full logs: https://github.com/{repo}/actions/runs/{run}")
    if not junit.is_file():
        lines.extend(["", "No pytest JUnit XML was produced. Failure occurred before",
                      "test report creation, or the test process could not start.",
                      "Read the complete failing step log; no error is suppressed."])
        return [], "\n".join(lines) + "\n"

    try:
        root = ET.parse(junit).getroot()
    except ET.ParseError as error:
        lines.extend(["", f"Malformed JUnit report: {error}",
                      "Read the original failing step log for unmodified stderr."])
        return [], "\n".join(lines) + "\n"
    cases = list(root.iter("testcase"))
    failures: list[str] = []
    for case in cases:
        for node in list(case):
            if node.tag not in {"failure", "error"}:
                continue
            identity = f"{case.get('classname', '')}::{case.get('name', 'unknown')}"
            failures.append(identity)
            detail = "\n".join([identity, node.get("message", ""), node.text or ""]).strip()
            print(f"::group::{_escape_annotation('Full traceback: ' + identity)}")
            print(detail)  # Full report content, no truncation.
            print("::endgroup::")
            summary_line = (node.get("message", "") or node.text or node.tag).splitlines()[0]
            print(f"::error title={_escape_annotation('pytest ' + identity)}::{_escape_annotation(summary_line)}")
    lines.extend(["", f"JUnit testcases recorded: {len(cases)}",
                  f"Failed/error cases: {len(failures)}"])
    if failures:
        lines.extend(["", "Failures:"])
        lines.extend(f"- `{item}`" for item in failures)
        lines.extend(["", "Full pytest exception traces, captured stdout/stderr,",
                      "and logs are in the original failed step and diagnostic report."])
    else:
        lines.extend(["", "JUnit reports no failed cases. A setup, packaging,",
                      "smoke-test, or publishing step failed. Inspect the failing",
                      "step's complete output and the retained diagnostic artifact."])
    return failures, "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    failures, summary = summarize(args.junit, args.label, dict(os.environ))
    print(summary, end="")
    print(f"::error title={_escape_annotation(args.label + ' failed')}::See failing step output and job summary; full logs are retained.")
    output = Path("ci-reports") / "failure-summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(summary, encoding="utf-8")
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with open(github_summary, "a", encoding="utf-8") as file:
            file.write(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
