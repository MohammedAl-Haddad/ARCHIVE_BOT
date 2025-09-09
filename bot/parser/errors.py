"""Common parsing error container."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParseError:
    """Information about a parsing error."""

    message: str
    details: Optional[str] = None


__all__ = ["ParseError"]

