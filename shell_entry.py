"""Launch the real PyMoviePrint GUI with files selected in Windows Explorer."""
from __future__ import annotations

import ctypes
import logging
import os
import shutil
import sys
import traceback
from pathlib import Path

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv'}
MUTEX_NAME = r'Local\PyMoviePrintExplorerRunning'


def selected_videos(arguments):
    result = []
    seen = set()
    for argument in arguments:
        path = Path(argument).expanduser().absolute()
        if not path.is_file():
            raise ValueError(f'Video file not found: {path}')
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f'Unsupported video extension: {path.suffix}')
        norm = os.path.normcase(str(path))
        if norm not in seen:
            seen.add(norm)
            result.append(str(path))
    return result


def show_error(message):
    if sys.platform == 'win32':
        ctypes.windll.user32.MessageBoxW(None, str(message), 'PyMoviePrint', 0x10)
    else:
        print(message, file=sys.stderr)


def acquire_mutex():
    if sys.platform != 'win32':
        return None
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel32.CreateMutexW
    create.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    create.restype = ctypes.c_void_p
    handle = create(None, 0, MUTEX_NAME)
    if not handle:
        raise OSError(ctypes.get_last_error(), 'Could not register application mutex')
    return handle


def release_mutex(handle):
    if handle and sys.platform == 'win32':
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle(handle)


def find_application_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def configure_ffmpeg():
    installed_bin = find_application_directory() / 'ffmpeg'
    if (installed_bin / 'ffmpeg.exe').is_file() and (installed_bin / 'ffprobe.exe').is_file():
        os.environ['PATH'] = str(installed_bin) + os.pathsep + os.environ.get('PATH', '')
    if not (shutil.which('ffmpeg') and shutil.which('ffprobe')):
        raise RuntimeError('FFmpeg and ffprobe are required. Install both using winget install Gyan.FFmpeg before launching.')


def main(argv=None, app_factory=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        paths = selected_videos(argv)
    except (ValueError, OSError) as error:
        show_error(error)
        return 2
    mutex = None
    try:
        mutex = acquire_mutex()
        os.chdir(find_application_directory())
        if app_factory is None:
            configure_ffmpeg()
            import movieprint_gui
            settings = Path.home() / '.pymovieprint'
            settings.mkdir(parents=True, exist_ok=True)
            movieprint_gui.SETTINGS_FILE = str(settings / 'movieprint_gui_settings.json')
            movieprint_gui.setup_file_logging()
            app_factory = movieprint_gui.MoviePrintApp
        app = app_factory()
        if paths:
            def import_explorer_selection():
                app._add_preview_paths(paths)
                if getattr(app, '_internal_input_paths', None) == paths:
                    logging.getLogger(__name__).info(
                        'Explorer source import confirmed: %d video(s)', len(paths)
                    )
            app.after_idle(import_explorer_selection)
        app.mainloop()
        return 0
    except Exception as error:
        log_dir = Path.home() / '.pymovieprint' / 'logs'
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / 'shell_entry.log').open('a', encoding='utf-8') as output:
                traceback.print_exc(file=output)
        except OSError:
            pass
        show_error(f'Could not start contact sheet editor:\n{error}')
        return 1
    finally:
        release_mutex(mutex)


if __name__ == '__main__':
    raise SystemExit(main())
