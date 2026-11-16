"""Fail-fast static gates; the Windows workflow also compiles and installs."""
from pathlib import Path
import ast
import json
import re
import subprocess
import sys
import pytest
from windows.generate_installer import EXTENSIONS, render

ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / 'windows' / 'PyMoviePrint.iss'


def test_installer_generated_script_has_no_drift():
    assert ISS.read_text(encoding='utf-8') == render()


def test_reuses_real_inno_managed_lifecycle():
    iss = ISS.read_text(encoding='utf-8')
    for directive in ('PrivilegesRequired=lowest', 'ChangesAssociations=yes',
                      'SetupMutex=PyMoviePrintExplorerLifecycle',
                      'AppMutex=Local\\PyMoviePrintExplorerRunning',
                      'CloseApplications=yes', 'RestartApplications=no'):
        assert directive in iss
    assert 'UninstallDisplayIcon={app}\\PyMoviePrint.exe' in iss
    assert 'SetupIconFile=PyMoviePrint.ico' in iss
    assert 'function LegacyVerbMatches(const Extension: String): Boolean;' in iss
    assert 'not LegacyVerbMatches(Extension)' in iss
    assert 'uninsdeletekey' not in iss.lower()
    assert 'RegDeleteKeyIncludingSubkeys' in iss
    assert "if VerbMatches(Extension) then" in iss
    assert 'function InitializeUninstall: Boolean;' in iss
    assert 'function PrepareToInstall(var NeedsRestart: Boolean): String;' in iss


def test_exact_file_types_and_quote_boundaries():
    code = (ROOT / 'shell_entry.py').read_text(encoding='utf-8')
    tree = ast.parse(code)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'VIDEO_EXTENSIONS' for t in n.targets))
    assert set(ast.literal_eval(assignment.value)) == set(EXTENSIONS)
    iss = ISS.read_text(encoding='utf-8')
    for ext in EXTENSIONS:
        assert f'Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\PyMoviePrint.ContactSheet' in iss
    assert iss.count('ValueName: "MultiSelectModel"; ValueData: "Document"') == len(EXTENSIONS)
    assert iss.count('ValueData: """{app}\\PyMoviePrint.exe"" ""%1"""') == len(EXTENSIONS)


def test_freeze_collects_upstream_runtime_assets():
    spec = (ROOT / 'windows' / 'PyMoviePrint.spec').read_text(encoding='utf-8')
    for required in ('collect_all(\'tkinterdnd2\')', 'collect_all(\'customtkinter\')',
                     'source_paths', 'movieprint-studio-v1.png', 'COLLECT('):
        assert required in spec


def test_installer_is_not_a_powershell_venv_mutator():
    assert not (ROOT / 'windows' / 'Install-PyMoviePrint.ps1').exists()
    assert not (ROOT / 'windows' / 'Uninstall-PyMoviePrint.ps1').exists()


def test_powershell_windows_smoke_file_is_parseable_on_windows():
    if sys.platform != 'win32':
        pytest.skip('PowerShell parser runs on Windows CI')
    path = ROOT / 'windows' / 'smoke-install.ps1'
    command = (
        "$t=$null; $e=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile('"
        + str(path).replace("'", "''")
        + "', [ref]$t, [ref]$e) | Out-Null; "
        "if ($e.Count -gt 0) { $e | Out-String | Write-Error; exit 1 }"
    )
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], check=True)


def test_workflow_has_complete_ordered_gates():
    workflow = (ROOT / '.github' / 'workflows' / 'windows-installer.yml').read_text(encoding='utf-8')
    steps = [
        'Install pinned direct dependencies',
        'Install FFmpeg required by upstream integration tests',
        'Run complete upstream and fork test suite',
        'Build Windows GUI executable',
        'Bundle pinned FFmpeg LGPL shared tools (hash verified)',
        'Install Inno Setup compiler',
        'Compile managed Windows installer',
        'Install, verify registry, upgrade, uninstall',
    ]
    positions = []
    for step in steps:
        marker = '      - name: ' + step
        assert workflow.count(marker) == 1, step
        positions.append(workflow.index(marker))
    assert positions == sorted(positions)
    assert "      - main" in workflow
    assert 'run: ./windows/Prepare-FFmpeg.ps1' in workflow
    pin = json.loads((ROOT / 'windows' / 'ffmpeg-runtime.lock.json').read_text(encoding='utf-8'))
    assert len(pin['sha256']) == 64
    assert pin['asset'].endswith('win64-lgpl-shared-9.0.zip')
    script = (ROOT / 'windows' / 'Prepare-FFmpeg.ps1').read_text(encoding='utf-8')
    assert 'Get-FileHash -LiteralPath $Archive -Algorithm SHA256' in script
    assert 'Copy-Item -Path (Join-Path $Bin' in script
    assert 'PROVENANCE.json' in script

def test_direct_exe_artifact_and_tagged_release_require_success():
    workflow = (ROOT / '.github' / 'workflows' / 'windows-installer.yml').read_text(encoding='utf-8')
    assert "    tags:\n      - 'v*'" in workflow
    assert "archive: false" in workflow
    assert "path: dist/PyMoviePrint-Setup.exe" in workflow
    assert "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9" in workflow
    assert "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333" in workflow
    assert "name: PyMoviePrint-Setup.exe" in workflow
    assert "    needs: installer" in workflow
    assert "    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "  contents: read" in workflow
    assert "      contents: write" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert 'bash scripts/ci/publish_release.sh' in workflow
    release_script = (ROOT / 'scripts' / 'ci' / 'publish_release.sh').read_text('utf-8')
    assert 'gh release create "$RELEASE_TAG" --draft --verify-tag' in release_script
    assert 'gh release upload "$RELEASE_TAG" "$installer"' in release_script
    assert 'gh release edit "$RELEASE_TAG" --draft=false' in release_script
    assert '--clobber' in release_script
    assert 'sha256sum "$installer"' in release_script
    assert 'published release asset differs from tested executable' in release_script
    assert "--verify-tag" in workflow
    assert 'asset_names' in workflow
    assert "if-no-files-found: error" in workflow
    assert "if: always()" not in workflow
    assert "PyMoviePrint-Windows-installer-${{ github.sha }}" not in workflow
