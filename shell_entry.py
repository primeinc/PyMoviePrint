"""Windows Explorer selected-file launcher for the PyMoviePrint GUI."""
from __future__ import annotations
import os
import sys
import traceback
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv"}


def selected_videos(arguments):
    found = []
    seen = set()
    for argument in arguments:
        path = Path(argument).expanduser().absolute()
        if not path.is_file():
            raise ValueError(f"Video file not found: {path}")
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video extension: {path.suffix}")
        if ";" in str(path):
            raise ValueError("Semicolons in filenames are not supported by the GUI source parser")
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            found.append(str(path))
    return found


def show_error(message):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(message), "PyMoviePrint", 0x10)
    else:
        print(message, file=sys.stderr)


def main(argv=None, app_factory=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        paths = selected_videos(argv)
    except (ValueError, OSError) as error:
        show_error(error)
        return 2
    try:
        home = Path(__file__).resolve().parent
        os.chdir(home)
        ffmpeg_marker = home / "ffmpeg-bin.txt"
        if ffmpeg_marker.is_file():
            bin_dir = ffmpeg_marker.read_text(encoding="utf-8-sig").strip()
            if bin_dir and (Path(bin_dir) / "ffmpeg.exe").is_file() and (Path(bin_dir) / "ffprobe.exe").is_file():
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        if app_factory is None:
            import movieprint_gui
            settings = Path.home() / ".pymovieprint"
            settings.mkdir(parents=True, exist_ok=True)
            movieprint_gui.SETTINGS_FILE = str(settings / "movieprint_gui_settings.json")
            movieprint_gui.setup_file_logging()
            app_factory = movieprint_gui.MoviePrintApp
        app = app_factory()
        if paths:
            app.after_idle(lambda: app._add_preview_paths(paths))
        app.mainloop()
        return 0
    except Exception as error:
        logs = Path.home() / ".pymovieprint" / "logs"
        try:
            logs.mkdir(parents=True, exist_ok=True)
            with (logs / "shell_entry.log").open("a", encoding="utf-8") as output:
                traceback.print_exc(file=output)
        except OSError:
            pass
        show_error(f"Failed to open video contact sheet editor:\n{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
