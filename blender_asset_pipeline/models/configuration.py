"""Validation configuration independent of Blender's property system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NamingConvention(str, Enum):
    """Supported object naming styles."""

    LOWER_SNAKE_CASE = "LOWER_SNAKE_CASE"
    UPPER_CAMEL_CASE = "UPPER_CAMEL_CASE"
    ANY = "ANY"


@dataclass(frozen=True)
class ValidationConfig:
    """Settings applied to one validation run."""

    max_triangle_count: int = 100_000
    naming_convention: NamingConvention = NamingConvention.LOWER_SNAKE_CASE
    required_prefix: str = ""
    transform_tolerance: float = 0.0001

    def __post_init__(self) -> None:
        if self.max_triangle_count < 0:
            raise ValueError("max_triangle_count must be non-negative")
        if self.transform_tolerance < 0:
            raise ValueError("transform_tolerance must be non-negative")
