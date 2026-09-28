"""Atomic UTF-8 report-file writing independent of Blender."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def ensure_json_extension(path: str | Path) -> Path:
    """Append ``.json`` unless the supplied path already has that suffix."""
    destination = Path(path)
    if destination.suffix.lower() != ".json":
        destination = destination.with_name(destination.name + ".json")
    return destination


def write_json_report(path: str | Path, json_text: str) -> Path:
    """Atomically write a complete UTF-8 JSON report and return its final path."""
    destination = ensure_json_extension(path)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(json_text.rstrip("\n") + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return destination
