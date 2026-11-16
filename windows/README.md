# Windows Explorer video contact sheet installer

This directory belongs to the real [primeinc/PyMoviePrint fork](https://github.com/primeinc/PyMoviePrint), based on `eldorado230/PyMoviePrint@a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7`.

## Install the built app

**After the Windows installer workflow passes:** download **`PyMoviePrint-Setup.exe` directly**, either from the [GitHub Releases page](https://github.com/primeinc/PyMoviePrint/releases) once a version is published, or from the successful [Windows installer Actions run](https://github.com/primeinc/PyMoviePrint/actions/workflows/windows-installer.yml). The Actions artifact is an uncompressed single `.exe`, not a ZIP. Releases are published automatically only for version tags (`v*`) on commits merged into `main` after Windows acceptance passes. GitHub still supplies its automatic source-code archive links, unrelated to the installer. The installer installs an isolated frozen PyMoviePrint GUI and creates a per-user Explorer **Create video contact sheet** verb for MP4, MKV, MOV, AVI, WMV and FLV files. No Python installation, administrator elevation or change to default video-player associations is required. **FFmpeg and ffprobe are bundled.** The build runs `windows/Prepare-FFmpeg.ps1`, which reads `windows/ffmpeg-runtime.lock.json`, verifies the archived LGPL build's SHA-256, stages its DLLs and license files, and records exact binary/source provenance. The frozen launcher refuses to fall back to unrelated executables in PATH.

The **Create video contact sheet** entry displays the PyMoviePrint filmstrip/play logo, generated from `windows/PyMoviePrint-icon.png` into a real multi-resolution `PyMoviePrint.ico` for Explorer, the app, and Setup. Windows 11: right-click a video, choose **Show more options**, then **Create video contact sheet**. On Windows 10 the entry appears in the classic context menu. PyMoviePrint starts with that video and generates an editable preview; adjust **Rows** and **Columns** before exporting. Multiple selections use the Windows `Document` model: each selected file launches its own editor instance (up to the Shell's normal 15-file limit). This is a real Explorer verb, not a Send To shortcut. No native first-level Windows 11 `IExplorerCommand` extension is provided.

Uninstall from **Windows Installed Apps**. The Inno Setup uninstall log manages files and registration, and the uninstall callback removes only verb keys whose menu, selection mode and exact command remain unchanged. User settings in `~/.pymovieprint` are not removed. If another program has changed a verb, that verb is preserved for manual reconciliation.

**Migration:** Remove any old standalone PowerShell-wrapper version first. The new installer deliberately refuses to overwrite a context-menu command it cannot identify as its own.

## Build and verify

On a Windows x64 machine with Python 3.11 and Inno Setup 6, from the repository root:

```powershell
python -m pip install -r windows/requirements-build.txt
python -m pytest -q
python windows/build_icon.py
python windows/generate_installer.py
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build/windows windows/PyMoviePrint.spec
powershell.exe -NoProfile -File windows/Prepare-FFmpeg.ps1
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" windows/PyMoviePrint.iss
.\windows\smoke-install.ps1
```

The workflow `.github/workflows/windows-installer.yml` runs these checks and uploads the **installer EXE only** as a direct-download artifact. On an eligible `v*` tag from `main`, a separate permissions-scoped job attaches the same CI-tested `.exe` to a GitHub Release. The build manifest and diagnostics remain in CI logs; they are not additional installer assets. It must actually run on Windows before this PR is mergeable; Linux-only source tests are insufficient. The Windows smoke script performs installation, registry-readback, real ShellExecute activation of a sample video, waits for a rendered contact-sheet preview, verifies the bundled FFmpeg executable, exercises upgrade and altered-verb refusal, and uninstalls. The inherited real-GUI tests also exercise rows/columns and PNG export. Require successful Windows CI for the **exact delivered commit** before distributing an installer.

Direct package versions are pinned in `windows/requirements-build.txt`; transitive packages are recorded in `build-info.json` by CI but are **not yet a fully hash-locked build**. The FFmpeg archive identity, SHA-256, source commit and build recipes are pinned in `windows/ffmpeg-runtime.lock.json`; the monthly upstream build is retained for two years. Review third-party LGPL/source obligations before broad public distribution. Do not claim bit-for-bit reproducibility from the source alone.

## Reference receipts

- Upstream UI: `eldorado230/PyMoviePrint@a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7 :: movieprint_gui.py#MoviePrintApp._add_preview_paths` and `movieprint_gui.spec`.
- Inno Setup: https://jrsoftware.org/inno-setup/documentation/topic_setupsection.htm , https://jrsoftware.org/inno-setup/documentation/topic_registrysection.htm
- Shell selection model: https://learn.microsoft.com/en-us/windows/win32/shell/how-to-employ-the-verb-selection-model
- PyInstaller build modes: https://pyinstaller.org/en/stable/spec-files.html

The monthly FFmpeg build is retained for two years under upstream release-retention policy; ordinary daily auto-builds are only retained for 14 days. This pin is deliberately not a floating latest URL.
