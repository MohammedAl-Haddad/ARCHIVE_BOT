"""Helper utilities for parser debugging."""
from __future__ import annotations

from typing import List

# This module exposes ``raw_tags`` which is populated by parsers to aid tests
# and debugging by capturing the raw hashtags extracted from message text.
raw_tags: List[str] | None = None

__all__ = ["raw_tags"]
