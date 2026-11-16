"""Workflow anti-stale-run and diagnostic contract, with negative controls."""
from pathlib import Path
import importlib.util
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
WIN = ROOT / ".github" / "workflows" / "windows-installer.yml"
REPORT = ROOT / "scripts" / "ci" / "report_failure.py"
GROUP = "  group: ${{ github.workflow }}-${{ github.event_name }}-${{ (github.event_name == 'workflow_dispatch' || github.ref_type == 'tag') && github.run_id || (github.head_ref || github.ref_name) }}"
CANCEL = "  cancel-in-progress: ${{ github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref_type != 'tag') }}"


def _correct_workflow(content):
    return (
        content.count("\nconcurrency:\n") == 1
        and GROUP in content
        and CANCEL in content
        and "    tags:\n      - 'v*'" in content if "Windows contact sheet installer" in content else
        content.count("\nconcurrency:\n") == 1 and GROUP in content and CANCEL in content
    )


def test_automatic_runs_cancel_stale_branch_work_not_tags_or_manual_runs():
    for workflow in (CI, WIN):
        contents = workflow.read_text(encoding="utf-8")
        assert _correct_workflow(contents)
        assert not _correct_workflow(contents.replace(CANCEL, "  cancel-in-progress: false"))
        assert "github.run_id" in contents  # tags and manual runs cannot cancel each other
        assert "github.workflow" in contents  # no cross-workflow cancellation


def test_branch_has_no_duplicate_push_and_pr_runs():
    ci = CI.read_text(encoding="utf-8")
    win = WIN.read_text(encoding="utf-8")
    assert "    branches:\n      - main" in ci
    assert "    branches:\n      - main" in win
    assert "      - feat/windows-explorer-contact-sheet" not in win
    assert "  pull_request:" in ci and "  pull_request:" in win


def test_failed_pytest_retains_tracebacks_and_junit_without_masking_exit():
    for workflow in (CI, WIN):
        contents = workflow.read_text(encoding="utf-8")
        assert "python -m pytest -q --tb=long -ra --show-capture=all --junitxml=ci-reports/pytest.xml" in contents
        assert "if: failure() && !cancelled()" in contents
        assert "scripts/ci/report_failure.py --junit ci-reports/pytest.xml" in contents
        assert "uses: actions/upload-artifact@v4" in contents
        assert "retention-days: 14" in contents
        assert "--maxfail" not in contents
        assert "continue-on-error: true" not in contents
        assert "2>&1 |" not in contents


def test_failure_report_lists_all_failing_cases_and_survives_missing_report(tmp_path):
    spec = importlib.util.spec_from_file_location("ci_failure_report", REPORT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    junit = tmp_path / "report.xml"
    root = ET.Element("testsuite")
    for name in ("test_one", "test_two"):
        case = ET.SubElement(root, "testcase", classname="module", name=name)
        ET.SubElement(case, "failure", message="test assertion failed").text = "complete traceback"
    ET.ElementTree(root).write(junit)
    failures, summary = module.summarize(junit, "demo", {"GITHUB_SHA": "abc"})
    assert len(failures) == 2
    assert "module::test_one" in summary and "module::test_two" in summary
    _, missing = module.summarize(tmp_path / "missing.xml", "demo", {})
    assert "No pytest JUnit XML" in missing
    assert "%0A" in module._escape_annotation("first\nsecond")
