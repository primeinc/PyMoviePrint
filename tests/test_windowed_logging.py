"""Regression for PyInstaller windowed bootloader with no stdio streams.

Canonical: pyinstaller.org/en/stable/common-issues-and-pitfalls.html
"""
import logging
from logging.handlers import RotatingFileHandler

import movieprint_gui as gui


def test_setup_file_logging_without_stdout_stderr(monkeypatch, tmp_path):
    root = logging.getLogger()
    original = list(root.handlers)
    with monkeypatch.context() as context:
        context.setattr(gui.sys, 'stdout', None)
        context.setattr(gui.sys, 'stderr', None)
        context.setattr(gui.os.path, 'expanduser', lambda _path: str(tmp_path / 'logs'))
        gui.setup_file_logging()
    added = [handler for handler in root.handlers if handler not in original]
    try:
        assert any(isinstance(handler, RotatingFileHandler) for handler in added)
        assert not [handler for handler in added
                    if isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, RotatingFileHandler)]
    finally:
        for handler in added:
            root.removeHandler(handler)
            handler.close()
