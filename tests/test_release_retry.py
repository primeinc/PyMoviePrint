"""Exercise release publishing as a crash/retry state machine with a fake gh CLI."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "publish_release.sh"
pytestmark = pytest.mark.skipif(sys.platform != "linux" or not shutil.which("bash") or not shutil.which("jq"),
                                reason="GitHub Releases run on Ubuntu; Windows bash.exe is an unavailable WSL launcher")


@pytest.fixture
def scenario(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state = tmp_path / "release-state.json"
    installer = tmp_path / "PyMoviePrint-Setup.exe"
    installer.write_bytes(b"MZ fake deterministic Windows test executable")
    fake_gh = bin_dir / "gh"
    fake_gh.write_text("""#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import sys

state_path = Path(os.environ["FAKE_GH_STATE"])
args = sys.argv[1:]
obj = json.loads(state_path.read_text()) if state_path.is_file() else None

if args[:2] == ["release", "view"]:
    if obj is None:
        print("release not found", file=sys.stderr)
        sys.exit(1)
    print(str(obj["draft"]).lower())
elif args[:2] == ["release", "create"]:
    if obj is not None:
        print("release already exists", file=sys.stderr)
        sys.exit(1)
    obj = {"draft": True, "assets": []}
    state_path.write_text(json.dumps(obj))
    print("draft release created")
elif args[:2] == ["release", "upload"]:
    if obj is None or not obj["draft"]:
        sys.exit(1)
    file = Path(args[3])
    digest = "sha256:" + hashlib.sha256(file.read_bytes()).hexdigest()
    obj["assets"] = [{"name": file.name, "digest": digest}]
    state_path.write_text(json.dumps(obj))
    print("uploaded installer")
elif args[:2] == ["release", "edit"]:
    if obj is None or not obj["assets"]:
        sys.exit(1)
    obj["draft"] = False
    state_path.write_text(json.dumps(obj))
    print("release published")
elif args[0] == "api":
    if any("/releases/tags/" in arg for arg in args):
        # Upstream REST endpoint intentionally hides draft releases.
        if obj is None or obj["draft"]:
            print("404", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(obj))
    elif any("releases?per_page=100" in arg for arg in args):
        # gh api --paginate --slurp wraps each response page in an array.
        print(json.dumps([[obj]] if obj is not None else [[]]))
    else:
        print("unexpected API:", args, file=sys.stderr)
        sys.exit(99)
else:
    print("unexpected gh call:", args, file=sys.stderr)
    sys.exit(99)
""", encoding="utf-8")
    fake_gh.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
               RELEASE_TAG="v0.0.0-test", GITHUB_REPOSITORY="primeinc/PyMoviePrint",
               INSTALLER_PATH=str(installer), FAKE_GH_STATE=str(state))
    return SCRIPT, env, state, installer


def _invoke(scenario):
    script, env, _, _ = scenario
    return subprocess.run(["bash", str(script)], env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_new_release_publishes_exactly_one_exe_and_rerun_is_idempotent(scenario):
    _, _, state, installer = scenario
    first = _invoke(scenario)
    assert first.returncode == 0, first.stdout + first.stderr
    metadata = json.loads(state.read_text())
    assert metadata == {"draft": False, "assets": [
        {"name": "PyMoviePrint-Setup.exe", "digest": _digest(installer)},
    ]}
    second = _invoke(scenario)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "Already published and verified" in second.stdout
    assert json.loads(state.read_text()) == metadata


@pytest.mark.parametrize("assets", [
    [],
    [{"name": "PyMoviePrint-Setup.exe", "digest": "sha256:outdated"}],
])
def test_interrupted_draft_is_repaired_then_published(scenario, assets):
    _, _, state, installer = scenario
    state.write_text(json.dumps({"draft": True, "assets": assets}))
    result = _invoke(scenario)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(state.read_text()) == {"draft": False, "assets": [
        {"name": "PyMoviePrint-Setup.exe", "digest": _digest(installer)},
    ]}


def test_published_wrong_exe_fails_and_does_not_mutate(scenario):
    _, _, state, _ = scenario
    bad = {"draft": False, "assets": [
        {"name": "PyMoviePrint-Setup.exe", "digest": "sha256:wrong"},
    ]}
    state.write_text(json.dumps(bad))
    result = _invoke(scenario)
    assert result.returncode != 0
    assert "published release asset differs from tested executable" in result.stderr.lower()
    assert json.loads(state.read_text()) == bad


def test_foreign_draft_asset_fails_and_does_not_mutate(scenario):
    _, _, state, _ = scenario
    bad = {"draft": True, "assets": [
        {"name": "other.zip", "digest": "sha256:other"},
    ]}
    state.write_text(json.dumps(bad))
    result = _invoke(scenario)
    assert result.returncode != 0
    assert json.loads(state.read_text()) == bad


def test_release_command_parses_on_host_shell():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr


def test_draft_lookups_use_list_endpoint_not_published_only_tag_endpoint():
    script = SCRIPT.read_text(encoding="utf-8")
    assert "gh api --paginate --slurp" in script
    assert "select(.tag_name == $tag)" in script
    assert 'gh api "repos/$GITHUB_REPOSITORY/releases/tags/$RELEASE_TAG"' not in script


def test_existing_draft_resumes_without_duplicate_release(scenario):
    _, _, state, installer = scenario
    state.write_text(json.dumps({"draft": True, "assets": []}))
    result = _invoke(scenario)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Existing release found (draft or published)" in result.stdout
    assert json.loads(state.read_text()) == {"draft": False, "assets": [
        {"name": "PyMoviePrint-Setup.exe", "digest": _digest(installer)},
    ]}
