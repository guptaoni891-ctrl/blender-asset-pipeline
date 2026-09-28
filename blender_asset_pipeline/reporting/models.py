"""Metadata models for public validation report generation."""

from __future__ import annotations

from dataclasses import dataclass

from ..batch.models import BatchValidationReport


@dataclass(frozen=True)
class ReportGenerator:
    """Tool metadata embedded in a machine-readable report."""

    tool_name: str
    addon_version: str
    blender_version: str | None = None


@dataclass(frozen=True)
class ReportSource:
    """Source blend-file metadata captured when validation ran."""

    blend_filepath: str | None
    is_saved: bool


@dataclass(frozen=True)
class LatestBatchRun:
    """One in-memory batch result and its matching report metadata."""

    run_id: str
    report: BatchValidationReport
    generator: ReportGenerator
    source: ReportSource
    generated_at_utc: str
