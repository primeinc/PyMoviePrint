"""Concurrent Explorer editors must never interleave saved settings JSON."""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

import movieprint_gui


def test_failed_json_serialization_preserves_existing_settings(tmp_path):
    target = tmp_path / "movieprint_settings.json"
    original = {"rows": 4, "input_paths_list": ["a.mp4", "b.mkv"]}
    movieprint_gui._save_settings_atomically(target, original)
    previous = target.read_bytes()

    with pytest.raises(TypeError):
        movieprint_gui._save_settings_atomically(target, {"unserializable": object()})

    assert target.read_bytes() == previous
    assert json.loads(target.read_text(encoding="utf-8")) == original
    assert not list(tmp_path.glob(".pymovieprint-settings-*.tmp"))


def test_replace_happens_only_after_new_json_is_complete(tmp_path, monkeypatch):
    target = tmp_path / "movieprint_settings.json"
    movieprint_gui._save_settings_atomically(target, {"version": 1})
    replace = os.replace
    replaced = []

    def checked_replace(src, dst):
        assert os.fspath(dst) == str(target)
        assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}
        assert json.loads(open(src, encoding="utf-8").read()) == {"version": 2}
        replaced.append((src, dst))
        return replace(src, dst)

    monkeypatch.setattr(movieprint_gui.os, "replace", checked_replace)
    movieprint_gui._save_settings_atomically(target, {"version": 2})

    assert len(replaced) == 1
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 2}


def test_simultaneous_editor_writes_leave_complete_valid_json(tmp_path):
    target = tmp_path / "movieprint_settings.json"

    def save(index):
        movieprint_gui._save_settings_atomically(target, {
            "editor": index, "sequence": index * 17,
            "payload": str(index) * 1000,
        })

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(save, range(32)))

    final = json.loads(target.read_text(encoding="utf-8"))
    assert 0 <= final["editor"] < 32
    assert final["sequence"] == final["editor"] * 17
    assert final["payload"] == str(final["editor"]) * 1000
    assert not list(tmp_path.glob(".pymovieprint-settings-*.tmp"))


def _save_from_subprocess(args):
    path, index = args
    from movieprint_gui import _save_settings_atomically
    _save_settings_atomically(path, {
        "editor": index,
        "sequence": index * 17,
        "payload": str(index) * 1000,
    })


def test_separate_editor_processes_never_corrupt_settings(tmp_path):
    """Windows shell verbs start separate processes, not just threads."""
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context

    target = tmp_path / "shared-settings.json"
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context("spawn")) as pool:
        list(pool.map(_save_from_subprocess, [(str(target), i) for i in range(12)]))

    final = json.loads(target.read_text(encoding="utf-8"))
    assert final["sequence"] == final["editor"] * 17
    assert final["payload"] == str(final["editor"]) * 1000
    assert not list(tmp_path.glob(".pymovieprint-settings-*.tmp"))


def test_kernel_file_lock_serializes_simultaneous_replacements(tmp_path, monkeypatch):
    """Negative control: the same instrumented workload overlaps without a lock."""
    import contextlib
    import threading
    import time

    target = tmp_path / "shared.json"
    original_replace = os.replace
    active = 0
    peak = 0
    gate = threading.Lock()

    def monitored_replace(src, dst):
        nonlocal active, peak
        with gate:
            active += 1
            peak = max(peak, active)
        time.sleep(0.01)
        try:
            return original_replace(src, dst)
        finally:
            with gate:
                active -= 1

    monkeypatch.setattr(movieprint_gui.os, "replace", monitored_replace)

    def run_round():
        nonlocal peak
        peak = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: movieprint_gui._save_settings_atomically(
                target, {"editor": i}), range(12)))
        return peak

    assert run_round() == 1

    # Mutate the guard away in-memory: the same verifier must detect overlap.
    monkeypatch.setattr(movieprint_gui, "FileLock", lambda *a, **kw: contextlib.nullcontext())
    # On Windows an overlapping os.replace might fail, which is itself the bug.
    try:
        unguarded_peak = run_round()
    except OSError:
        unguarded_peak = peak
    assert unguarded_peak > 1
