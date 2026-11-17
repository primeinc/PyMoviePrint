"""CI must use the same pinned runtime as the Windows deliverable."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_both_windows_ci_flows_resolve_pinned_ffmpeg():
    for path in (
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "windows-installer.yml",
    ):
        text = path.read_text(encoding="utf-8")
        assert "./windows/Prepare-FFmpeg.ps1 -Destination $bin" in text
        assert "Add-Content -LiteralPath $env:GITHUB_PATH -Value $bin" in text
        assert "choco install ffmpeg" not in text
        assert "Pinned FFmpeg failed to start" in text
