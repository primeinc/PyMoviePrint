"""Preserve structured video selection paths despite the legacy semicolon entry."""
from __future__ import annotations
from pathlib import Path
from typing import Sequence


def resolve_source_paths(display_value: str, selected_paths: Sequence[str] = ()) -> list[str]:
    current = [str(path) for path in selected_paths if str(path)]
    if display_value == '; '.join(current):
        return current
    typed = display_value.strip()
    if not typed:
        return []
    if Path(typed).exists():
        return [typed]
    return [part.strip() for part in typed.split(';') if part.strip()]
