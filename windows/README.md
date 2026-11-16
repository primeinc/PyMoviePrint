# Windows Explorer contact-sheet installer

This installer is included in the actual [primeinc/PyMoviePrint](https://github.com/primeinc/PyMoviePrint) GitHub fork, based on upstream eldorado230/PyMoviePrint at a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7.

Download the **complete fork repository ZIP** or clone it, then double-click **windows/Install.cmd**.

The installer copies the application source **from this checkout** to the current user's Local AppData Programs folder; it does not download an unrelated upstream package. It sets up Python 3.11 and FFmpeg when needed (through winget), installs requirements in its own virtual environment, and adds a **Create video contact sheet** command to the right-click menu for MP4, MKV, MOV, AVI, WMV and FLV videos. No administrator rights or default-file-association changes are needed for registration.

On Windows 11: right-click the video, select **Show more options**, then **Create video contact sheet**. Windows 10 normally shows the command directly. The GUI opens with the selected file and an editable preview. Change the existing Rows/Columns controls, then export.

Uninstall using **windows/Uninstall.cmd** or the Windows Installed Apps entry. Personal settings are preserved. Re-running the installer updates only a previously managed installation.

This is a genuine per-user Windows Explorer shell verb, **not** a Send To shortcut. It does **not** provide a first-level Windows 11 modern menu entry, which requires a packaged IExplorerCommand COM extension. It also explicitly rejects video names containing semicolons because the upstream GUI parses source paths with semicolon separators.

Verification: run `python -m pytest -q tests/test_shell_entry.py tests/test_windows_install_files.py`. The Windows CI parses both PowerShell scripts; an actual Windows installation and Explorer invocation still require acceptance testing on Windows.

Source: [upstream README](https://github.com/eldorado230/PyMoviePrint/blob/a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7/README.md) and movieprint_gui.py symbols MoviePrintApp._add_preview_paths, _on_col_slider_change and _on_row_slider_change.
