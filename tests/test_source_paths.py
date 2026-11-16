from pathlib import Path
import tempfile
from source_paths import resolve_source_paths


def test_selected_semicolon_path_remains_exact():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'scene;part 2.mp4'
        path.touch()
        assert resolve_source_paths(str(path), [str(path)]) == [str(path)]
        assert resolve_source_paths(str(path), []) == [str(path)]


def test_mixed_selected_paths_preserve_all():
    paths = [r'C:\Movie\a;b.mp4', r'C:\Movie\two spaces.mkv']
    assert resolve_source_paths('; '.join(paths), paths) == paths


def test_editing_field_replaces_selection():
    assert resolve_source_paths('new.avi', ['old.mp4']) == ['new.avi']


def test_legacy_delimited_list_still_works():
    assert resolve_source_paths('a.mov; b.mp4', []) == ['a.mov', 'b.mp4']


def test_empty_text():
    assert resolve_source_paths('', ['old.mp4']) == []
