"""Parsing utilities for hashtag based ingestion backed by the database.

All hashtag aliases and their mappings are stored in the database and are
resolved at runtime via :mod:`bot.repo.hashtags`.  Only the ordering rules are
coded here.  Errors are reported using short codes so the caller can provide
localised messages.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Tuple

from ..utils.formatting import arabic_ordinal, to_display_name, ARABIC_ORDINALS
from ..repo import hashtags, taxonomy

# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------
BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e]")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _clean(text: str) -> str:
    """Return *text* without direction markers and with normalised digits."""

    return BIDI_RE.sub("", text).translate(_ARABIC_DIGITS)


# ---------------------------------------------------------------------------
# Tag extraction helpers
# ---------------------------------------------------------------------------
LECTURER_PREFIXES: Tuple[str, ...] = (
    "الدكتور_",
    "الدكتورة_",
    "الأستاذ_",
    "الأستاذة_",
    "المهندس_",
    "المهندسة_",
    "م_",
    "م",
)

ORDINAL_WORDS = {v: k for k, v in ARABIC_ORDINALS.items()}
YEAR_TAG_RE = re.compile(r"^#(\d{4})(?:هـ|ه)?$")
LECTURE_TAG_RE = re.compile(r"^#([^_]+)_(.+?)(?::\s*(.+))?$")


@dataclass
class ParsedHashtags:
    content_type: str | None = None
    lecture_no: int | None = None
    lecture_no_display: str | None = None
    title: str | None = None
    year: int | None = None
    lecturer: str | None = None
    tags: List[str] | None = None


async def classify_hashtag(tag: str) -> Tuple[str | None, str | None]:
    """Classify a single hashtag into ("card"|"sec", code)."""

    token = tag.strip()
    if not token.startswith("#"):
        return None, None
    alias = token[1:]
    rows = await hashtags.get_mappings_for_alias(alias)
    if not rows:
        return None, None
    row = rows[0]
    alias_row = await hashtags.get_alias(alias)
    if row[2] == "card":
        return "card", alias_row[2]
    if row[2] == "section":
        return "sec", alias_row[2]
    return None, None


def _split_lines(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            lines.append(s)
    return lines


async def parse_hashtags(text: str) -> Tuple[ParsedHashtags, str | None]:
    """Parse *text* and return ``(info, error_code)``."""

    cleaned = _clean(text or "")
    tags = _split_lines(cleaned)
    info = ParsedHashtags(tags=tags)
    if not tags:
        return info, "E-NO-CONTEXT"

    step = "content"
    item_type = None

    for raw in tags:
        token = raw.split()[0]
        alias = token.lstrip("#")

        if step == "content":
            rows = await hashtags.get_mappings_for_alias(alias)
            if not rows:
                return info, "E-ALIAS-UNKNOWN"
            row = rows[0]
            if not row[4]:  # not a content tag
                return info, "E-NO-CONTEXT"
            if info.content_type is not None:
                return info, "E-HT-MULTI"
            alias_row = await hashtags.get_alias(alias)
            info.content_type = alias_row[2]
            item_type = await taxonomy.get_item_type(info.content_type)
            step = "meta"
            continue

        m = YEAR_TAG_RE.match(token)
        if m:
            info.year = int(m.group(1))
            continue

        if info.lecturer is None:
            norm = alias
            for p in LECTURER_PREFIXES:
                if norm.startswith(p):
                    info.lecturer = to_display_name(norm[len(p):])
                    break
            if info.lecturer is not None:
                continue

        m = LECTURE_TAG_RE.match(raw)
        if m and info.lecture_no is None:
            prefix, ident, title = m.groups()
            if await hashtags.get_alias(prefix) is None:
                return info, "E-ALIAS-UNKNOWN"
            ident = ident.strip()
            if ident.isdigit():
                info.lecture_no = int(ident)
            else:
                info.lecture_no = ORDINAL_WORDS.get(ident)
            if info.lecture_no:
                info.lecture_no_display = arabic_ordinal(info.lecture_no)
            if title:
                info.title = title.strip()
            step = "done"
            continue

        if await hashtags.get_alias(alias) is None:
            return info, "E-ALIAS-UNKNOWN"

    if info.content_type is None:
        return info, "E-NO-CONTEXT"
    if item_type and item_type[4] and info.lecture_no is None:
        return info, "E-NO-SESSION"

    return info, None


__all__ = ["parse_hashtags", "ParsedHashtags", "classify_hashtag"]
