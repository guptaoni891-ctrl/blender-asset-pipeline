"""Lifecycle-managed in-memory storage for the latest batch run."""

from __future__ import annotations

from .models import LatestBatchRun

_latest_batch_run: LatestBatchRun | None = None


def set_latest_batch_run(run: LatestBatchRun) -> None:
    """Replace the cached run used by JSON export."""
    global _latest_batch_run
    _latest_batch_run = run


def get_latest_batch_run(run_id: str) -> LatestBatchRun | None:
    """Return the cached run only when it matches the displayed UI state."""
    if _latest_batch_run is None or _latest_batch_run.run_id != run_id:
        return None
    return _latest_batch_run


def clear_latest_batch_run() -> None:
    """Discard cached report data during invalidation or unregister."""
    global _latest_batch_run
    _latest_batch_run = None
