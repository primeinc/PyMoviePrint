"""Regression: a grid can request more thumbnails than a short video has frames."""
import logging
import shutil
import subprocess
from pathlib import Path

import pytest

from video_processing import VideoExtractor


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="Requires FFmpeg")
def test_short_low_fps_video_has_valid_last_thumbnail_for_each_grid_slot(tmp_path):
    video = tmp_path / "scene; selection.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=4:duration=2",
        "-c:v", "mpeg4", "-q:v", "6", "-an", str(video),
    ], capture_output=True, check=True, timeout=30)

    # A 5x5 contact sheet requests frames after 1.75s even though the
    # 2-second, 4-fps fixture's final real frame is at 1.75 seconds.
    requested = [(i + 1) * 2.0 / 26.0 for i in range(25)]
    assert requested[-1] > 1.75
    with VideoExtractor(str(video), logging.getLogger("test_short_video")) as extractor:
        fps, duration, frame_count = extractor.properties
        assert fps == pytest.approx(4.0)
        assert duration == pytest.approx(2.0)
        assert frame_count == 8
        frames = extractor.extract_timestamps_optimized(requested, str(tmp_path / "frames"))

    assert len(frames) == 25
    assert all(Path(frame["frame_path"]).stat().st_size > 0 for frame in frames)
    assert [frame["timestamp_sec"] for frame in frames] == pytest.approx(requested)
    assert [frame["frame_number"] for frame in frames[-3:]] == [7, 7, 7]


def test_final_one_frame_shot_is_not_dropped_when_seek_is_clamped(tmp_path, monkeypatch):
    """Scene association uses the requested midpoint even when FFmpeg seeks earlier."""
    from unittest.mock import Mock
    import video_processing as vp

    video = tmp_path / "two-scenes.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=4:duration=2",
        "-c:v", "mpeg4", "-q:v", "6", "-an", str(video),
    ], capture_output=True, check=True, timeout=30)

    class FrameTime:
        def __init__(self, second, frame):
            self.second = second
            self.frame = frame

        def get_seconds(self):
            return self.second

        def get_frames(self):
            return self.frame

    manager = Mock()
    manager.get_scene_list.return_value = [
        (FrameTime(0.0, 0), FrameTime(1.75, 7)),
        (FrameTime(1.75, 7), FrameTime(2.0, 8)),
    ]
    stats = Mock()
    stats.get_metrics.return_value = [0.0]
    monkeypatch.setattr(vp, "SCENEDETECT_AVAILABLE", True)
    monkeypatch.setattr(vp, "StatsManager", lambda: stats, raising=False)
    monkeypatch.setattr(vp, "SceneManager", lambda stats_manager: manager, raising=False)
    monkeypatch.setattr(vp, "ContentDetector", lambda threshold: object(), raising=False)
    monkeypatch.setattr(vp, "open_video", lambda path: object(), raising=False)

    with VideoExtractor(str(video), logging.getLogger("test_tail_shot")) as extractor:
        shots = extractor.extract_shots(str(tmp_path / "shots"))

    assert len(shots) == 2, "The final one-frame scene must survive shot association"
    assert [shot["timestamp_sec"] for shot in shots] == pytest.approx([0.875, 1.875])
    assert shots[-1]["frame_number"] == 7
    assert shots[-1]["scene_start_sec"] == pytest.approx(1.75)
    assert shots[-1]["scene_end_sec"] == pytest.approx(2.0)
