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
        self.ran = False

    def after_idle(self, callback):
        self.after.append(callback)

    def _add_preview_paths(self, paths):
        self.loaded = paths

    def mainloop(self):
        self.ran = True
        for callback in self.after:
            callback()


class ExplorerLauncherTests(unittest.TestCase):
    def test_no_args_starts_empty_gui(self):
        app = FakeApp()
        with patch("shell_entry.os.chdir"):
            self.assertEqual(shell_entry.main([], lambda: app), 0)
        self.assertTrue(app.ran)
        self.assertIsNone(app.loaded)

    def test_selected_filename_passed_to_gui(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "my décor & (2).MP4"
            video.touch()
            app = FakeApp()
            with patch("shell_entry.os.chdir"):
                self.assertEqual(shell_entry.main([str(video)], lambda: app), 0)
            self.assertEqual(app.loaded, [str(video.absolute())])

    def test_shell_metacharacters_are_filename_data(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "name %TMP% & !value! ^(1).mkv"
            video.touch()
            self.assertEqual(shell_entry.selected_videos([str(video)]), [str(video.absolute())])

    def test_no_duplicate_videos(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "clip.flv"
            video.touch()
            self.assertEqual(shell_entry.selected_videos([str(video), str(video)]), [str(video.absolute())])

    def test_unsupported_extension_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "clip.txt"
            video.touch()
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                shell_entry.selected_videos([str(video)])

    def test_semicolon_filename_rejected_instead_of_splitting(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "episode;part2.mp4"
            video.touch()
            with self.assertRaisesRegex(ValueError, "Semicolons"):
                shell_entry.selected_videos([str(video)])

    def test_missing_video_prevents_gui_start(self):
        with patch("shell_entry.show_error") as error:
            result = shell_entry.main(["/this/path/does/not/exist.mp4"], FakeApp)
        self.assertEqual(result, 2)
        error.assert_called_once()

    def test_application_failure_not_silent(self):
        with patch("shell_entry.os.chdir"), patch("shell_entry.show_error") as error:
            def broken():
                raise RuntimeError("bad init")
            self.assertEqual(shell_entry.main([], broken), 1)
        error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
