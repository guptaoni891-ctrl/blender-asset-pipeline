"""Public machine-readable reporting API."""

from .json_report import batch_report_to_dict, batch_report_to_json
from .models import LatestBatchRun, ReportGenerator, ReportSource
from .writer import ensure_json_extension, write_json_report

__all__ = [
    "LatestBatchRun",
    "ReportGenerator",
    "ReportSource",
    "batch_report_to_dict",
    "batch_report_to_json",
    "ensure_json_extension",
    "write_json_report",
]
