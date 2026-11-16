"""Static safety checks and Windows-only PowerShell syntax validation."""
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
WIN = ROOT / "windows"


def test_installer_runs_from_checkout_and_registers_real_explorer_verb():
    source = (WIN / "Install-PyMoviePrint.ps1").read_text(encoding="utf-8")
    assert "Join-Path $PSScriptRoot '..'" in source
    assert "SystemFileAssociations" in source
    assert '"%1"' in source
    assert "pythonw.exe" in source
    assert "source='primeinc/PyMoviePrint'" in source
    assert (ROOT / "shell_entry.py").exists()


def test_uninstall_and_launcher_exist():
    assert (WIN / "Install.cmd").exists()
    assert (WIN / "Uninstall.cmd").exists()
    uninstall = (WIN / "Uninstall-PyMoviePrint.ps1").read_text(encoding="utf-8")
    assert "DeleteSubKeyTree" in uninstall
    assert "Test-Path -LiteralPath $Marker" in uninstall


def test_powershell_parser_on_windows():
    if sys.platform != "win32":
        pytest.skip("Windows PowerShell parser runs only on Windows CI")
    for script in ("Install-PyMoviePrint.ps1", "Uninstall-PyMoviePrint.ps1"):
        path = WIN / script
        code = (
            "$t=$null; $e=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'" + str(path).replace("'", "''") + "', [ref]$t, [ref]$e) | Out-Null; "
            "if ($e.Count -gt 0) { $e | Out-String | Write-Error; exit 1 }"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code], check=True)
