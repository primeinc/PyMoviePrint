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
    assert [frame["timestamp_sec"] for frame in frames[-3:]] == pytest.approx([1.75] * 3)
    assert [frame["frame_number"] for frame in frames[-3:]] == [7, 7, 7]
