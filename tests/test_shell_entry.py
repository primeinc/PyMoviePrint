import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import shell_entry


class FakeApp:
    def __init__(self):
        self.after = []
        self.loaded = None
        self._internal_input_paths = []
        self.ran = False

    def after_idle(self, callback):
        self.after.append(callback)

    def _add_preview_paths(self, paths):
        self.loaded = paths
        self._internal_input_paths = paths

    def mainloop(self):
        self.ran = True
        for callback in self.after:
            callback()


class ExplorerLauncherTests(unittest.TestCase):
    def test_no_args_starts_empty_gui(self):
        app = FakeApp()
        with patch('shell_entry.os.chdir'):
            self.assertEqual(shell_entry.main([], lambda: app), 0)
        self.assertTrue(app.ran)
        self.assertIsNone(app.loaded)

    def test_selected_filename_passed_to_gui(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'my décor & (2).MP4'
            video.touch()
            app = FakeApp()
            with patch('shell_entry.os.chdir'):
                self.assertEqual(shell_entry.main([str(video)], lambda: app), 0)
            self.assertEqual(app.loaded, [str(video.absolute())])

    def test_shell_metacharacters_are_filename_data(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'name %TMP% & !value! ^(1).mkv'
            video.touch()
            self.assertEqual(shell_entry.selected_videos([str(video)]), [str(video.absolute())])

    def test_no_duplicate_videos(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'clip.flv'
            video.touch()
            self.assertEqual(shell_entry.selected_videos([str(video), str(video)]), [str(video.absolute())])

    def test_unsupported_extension_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'clip.txt'
            video.touch()
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                shell_entry.selected_videos([str(video)])

    def test_selected_video_emits_runtime_import_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'scene; with space.mp4'
            video.touch()
            app = FakeApp()
            with patch('shell_entry.os.chdir'):
                with self.assertLogs('shell_entry', level='INFO') as captured:
                    self.assertEqual(shell_entry.main([str(video)], lambda: app), 0)
            self.assertIn('Explorer source import confirmed: 1 video(s)', captured.output[0])

    def test_semicolon_filename_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / 'episode;part2.mp4'
            video.touch()
            self.assertEqual(shell_entry.selected_videos([str(video)]), [str(video.absolute())])

    def test_missing_video_prevents_gui_start(self):
        with patch('shell_entry.show_error') as error:
            result = shell_entry.main(['/this/path/does/not/exist.mp4'], FakeApp)
        self.assertEqual(result, 2)
        error.assert_called_once()

    def test_application_failure_not_silent(self):
        with patch('shell_entry.os.chdir'), patch('shell_entry.show_error') as error:
            def broken():
                raise RuntimeError('bad init')
            self.assertEqual(shell_entry.main([], broken), 1)
        error.assert_called_once()

    def test_require_both_ffmpeg_and_ffprobe(self):
        with patch('shell_entry.shutil.which', side_effect=lambda x: '/usr/bin/ffmpeg' if x == 'ffmpeg' else None):
            with self.assertRaisesRegex(RuntimeError, 'ffprobe'):
                shell_entry.configure_ffmpeg()

    def test_require_binary_paths_without_scanning(self):
        with patch('shell_entry.shutil.which', return_value='/fake/bin'):
            shell_entry.configure_ffmpeg()


if __name__ == '__main__':
    unittest.main()


class BundledRuntimeTests(unittest.TestCase):
    def test_frozen_install_refuses_host_path_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(shell_entry.sys, 'frozen', True, create=True):
                with patch('shell_entry.find_application_directory', return_value=Path(root)):
                    with patch('shell_entry.shutil.which', return_value='C:/untrusted/ffmpeg.exe'):
                        with self.assertRaisesRegex(RuntimeError, 'installed FFmpeg runtime'):
                            shell_entry.configure_ffmpeg()

    def test_frozen_install_prepends_bundled_tools(self):
        with tempfile.TemporaryDirectory() as root:
            tools = Path(root) / 'ffmpeg'
            tools.mkdir()
            (tools / 'ffmpeg.exe').touch()
            (tools / 'ffprobe.exe').touch()
            with patch.object(shell_entry.sys, 'frozen', True, create=True):
                with patch('shell_entry.find_application_directory', return_value=Path(root)):
                    with patch.dict(os.environ, {'PATH': 'C:/other'}, clear=False):
                        shell_entry.configure_ffmpeg()
                        self.assertEqual(os.environ['PATH'].split(os.pathsep)[0], str(tools))
