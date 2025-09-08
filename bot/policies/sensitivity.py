"""Basic PHI/PII sensitivity policy."""

from __future__ import annotations

import json
import logging
import pathlib
import re
from typing import Optional

logger = logging.getLogger(__name__)


class SensitivityPolicy:
    """Detect sensitive personal or health information in text or filenames."""

    def __init__(self, patterns_file: str | None = None) -> None:
        path = (
            pathlib.Path(patterns_file)
            if patterns_file
            else pathlib.Path(__file__).with_name("sensitivity_patterns.json")
        )
        data: dict[str, list[str]] = {"keywords": [], "patterns": []}
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:  # pragma: no cover - safeguard
                logger.exception("Failed to load sensitivity patterns from %s", path)
        self.keywords = [kw.lower() for kw in data.get("keywords", [])]
        self.patterns = [re.compile(pat, re.IGNORECASE) for pat in data.get("patterns", [])]

    def is_sensitive(
        self,
        text: str,
        *,
        filename: str | None = None,
        section: str | None = None,
    ) -> bool:
        """Return True if *text* or *filename* contain sensitive info.

        A stricter threshold is used for specific *section* contexts like
        "clinical" or "case_study".
        """

        content = " ".join(part for part in [text, filename] if part)
        lowered = content.lower()
        hits = 0
        for kw in self.keywords:
            if kw in lowered:
                hits += 1
        for pat in self.patterns:
            if pat.search(content):
                hits += 1
        threshold = 1 if section in {"clinical", "case_study"} else 2
        return hits >= threshold


policy = SensitivityPolicy()

__all__ = ["SensitivityPolicy", "policy"]
