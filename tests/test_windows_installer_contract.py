"""Fail-fast static gates; the Windows workflow also compiles and installs."""
from pathlib import Path
import ast
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
    assert 'e907b01fa4783913151237e37df2a10fa97d99a1598a021bf59d4ae62ffed4c0' in workflow
    assert 'Copy-Item -Path (Join-Path $bin' in workflow
