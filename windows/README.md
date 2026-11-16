# Windows Explorer installer (draft PR #1)

This directory belongs to the real [primeinc/PyMoviePrint fork](https://github.com/primeinc/PyMoviePrint), based on `eldorado230/PyMoviePrint@a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7`.

## Install the built app

**Only after the Windows installer workflow has passed:** download `PyMoviePrint-Setup.exe` from that workflow's artifact (or a verified release), and run it. The installer installs an isolated frozen PyMoviePrint GUI and creates a per-user Explorer **Create video contact sheet** verb for MP4, MKV, MOV, AVI, WMV and FLV files. No Python installation, administrator elevation or change to default video-player associations is required. **FFmpeg and ffprobe are bundled** from the pinned FFmpeg LGPL shared distribution; the Windows build verifies SHA-256 before packaging. See `ffmpeg/licenses/PROVENANCE.txt` in the installed application for binary build, source commit, and licensing references. On a failed bundled-binary check, installation MUST fail, not silently fall back to random PATH binaries.

Windows 11: right-click a video, choose **Show more options**, then **Create video contact sheet**. On Windows 10 the entry appears in the classic context menu. PyMoviePrint starts with that video and generates an editable preview; adjust **Rows** and **Columns** before exporting. Multiple selections use the Windows `Document` model: each selected file launches its own editor instance (up to the Shell's normal 15-file limit). This is a real Explorer verb, not a Send To shortcut. No native first-level Windows 11 `IExplorerCommand` extension is provided.

Uninstall from **Windows Installed Apps**. The Inno Setup uninstall log manages files and registration, and the uninstall callback removes only verb keys whose menu, selection mode and exact command remain unchanged. User settings in `~/.pymovieprint` are not removed. If another program has changed a verb, that verb is preserved for manual reconciliation.

**Migration:** Remove any old standalone PowerShell-wrapper version first. The new installer deliberately refuses to overwrite a context-menu command it cannot identify as its own.

## Build and verify

On a Windows x64 machine with Python 3.11 and Inno Setup 6, from the repository root:

```powershell
python -m pip install -r windows/requirements-build.txt
python -m pytest -q
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/windows windows/PyMoviePrint.spec
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" windows/PyMoviePrint.iss
.\windows\smoke-install.ps1
```

The workflow `.github/workflows/windows-installer.yml` runs these checks and stores the installer plus dependency manifest. It must actually run on Windows before this PR is mergeable; Linux-only source tests are insufficient. The Windows smoke script performs install, upgrade, registry-readback, altered-verb refusal, and uninstall tests. It does not establish usability or preview/export correctness until a real GUI acceptance run passes.

Direct package versions are pinned in `windows/requirements-build.txt`; transitive packages are recorded in `build-info.json` by CI but are **not yet a fully hash-locked build**. Bundled FFmpeg archive is pinned to `autobuild-2026-11-15-12-40` with SHA-256 `6305750bb1b4e3f80d17a6644fec1cf57eef12106c4f9192ddb05e14a6b522b0`, produced from FFmpeg source `d838f9f9aeb0e09b4d068e2af20a46a12640696f` and FFmpeg-Builds scripts `c9fe5114060e507409f7ee07edfd82efaf25d767`. Review license obligations for *all third-party components* before public release. Do not claim bit-for-bit reproducibility from the source alone.

## Reference receipts

- Upstream UI: `eldorado230/PyMoviePrint@a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7 :: movieprint_gui.py#MoviePrintApp._add_preview_paths` and `movieprint_gui.spec`.
- Inno Setup: https://jrsoftware.org/inno-setup/documentation/topic_setupsection.htm , https://jrsoftware.org/inno-setup/documentation/topic_registrysection.htm
- Shell selection model: https://learn.microsoft.com/en-us/windows/win32/shell/how-to-employ-the-verb-selection-model
- PyInstaller build modes: https://pyinstaller.org/en/stable/spec-files.html
