from __future__ import annotations

"""Caption parsing utilities.

This module exposes a single public interface :func:`parse_message` which is
used by other parts of the bot to extract information from a message caption or
body.  The actual parsing logic will be implemented in subsequent iterations;
for now the function simply wraps the provided values in lightweight data
containers so the rest of the codebase can interact with a stable API.
"""

from dataclasses import dataclass
import json
import re
from typing import List, Optional, Tuple

from ..repo import RepoNotFound, hashtags, taxonomy
from ..utils.formatting import to_display_name
from .hashtags import YEAR_TAG_RE, LECTURE_TAG_RE, LECTURER_PREFIXES
from . import helpers

BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e]")
HASHTAG_RE = re.compile(r"#([^\s#]+)")


@dataclass
class ParseResult:
    """Result of a successful parsing operation."""

    text: str
    group_id: Optional[int] = None
    tg_topic_id: Optional[int] = None
    locale: Optional[str] = None
    hashtags: Optional[List[dict]] = None
    content_tag: Optional[dict] = None
    year: Optional[int] = None
    lecturer: Optional[str] = None


@dataclass
class ParseError:
    """Information about a parsing error."""

    message: str
    details: Optional[str] = None


async def parse_message(
    message_text: str,
    group_id: Optional[int] = None,
    tg_topic_id: Optional[int] = None,
    user_locale: Optional[str] = None,
) -> Tuple[ParseResult, Optional[ParseError]]:
    """Parse *message_text* and return ``(result, error)``.

    Extract hashtags using :data:`HASHTAG_RE`, normalise Arabic digits and
    case using :func:`hashtags.normalize_alias`, resolve their targets using
    :func:`hashtags.resolve_content_tag`, and remove direction markers so the
    comparison is case and direction insensitive.
    """

    clean_text = BIDI_RE.sub("", message_text)
    matches = list(HASHTAG_RE.finditer(clean_text))
    helpers.raw_tags = [m.group(0) for m in matches]
    seen: set[str] = set()
    tags: List[dict] = []
    content_tags: List[dict] = []
    year: Optional[int] = None
    lecturer: Optional[str] = None
    lecture_no: Optional[int] = None
    card_ids: set[int] = set()
    item_type_ids: set[int] = set()
    for m in matches:
        tag = m.group(1)
        normalized = hashtags.normalize_alias(tag)
        if normalized in seen:
            continue
        seen.add(normalized)

        m_year = YEAR_TAG_RE.match(f"#{normalized}")
        if m_year and year is None:
            y = int(m_year.group(1))
            if 1300 <= y <= 1600 or 1900 <= y <= 2100:
                year = y
            continue

        if lecturer is None:
            for p in LECTURER_PREFIXES:
                if normalized.startswith(p):
                    lecturer = to_display_name(normalized[len(p):])
                    break
            if lecturer is not None:
                continue

        if lecture_no is None:
            m_lecture = LECTURE_TAG_RE.match(f"#{normalized}")
            if m_lecture:
                ident = m_lecture.group(1)
                if ident.isdigit():
                    lecture_no = int(ident)
                continue

        try:
            resolved = await hashtags.resolve_content_tag(normalized)
        except RepoNotFound:
            result = ParseResult(
                text=message_text,
                group_id=group_id,
                tg_topic_id=tg_topic_id,
                locale=user_locale,
                hashtags=None,
                content_tag=None,
                year=year,
                lecturer=lecturer,
            )
            return result, ParseError("E-HT-UNKNOWN")
        tags.append(resolved)
        if resolved.get("is_content_tag"):
            content_tags.append(resolved)
        if resolved.get("target_kind") == "card":
            card_ids.add(resolved["target_id"])
        elif resolved.get("target_kind") == "item_type":
            item_type_ids.add(resolved["target_id"])
    if not content_tags:
        result = ParseResult(
            text=message_text,
            group_id=group_id,
            tg_topic_id=tg_topic_id,
            locale=user_locale,
            hashtags=tags or None,
            content_tag=None,
            year=year,
            lecturer=lecturer,
        )
        return result, ParseError("E-NO-CONTENT-TAG")
    if len(content_tags) > 1:
        result = ParseResult(
            text=message_text,
            group_id=group_id,
            tg_topic_id=tg_topic_id,
            locale=user_locale,
            hashtags=tags or None,
            content_tag=None,
            year=year,
            lecturer=lecturer,
        )
        return result, ParseError("E-HT-MULTI")

    content_tag = content_tags[0]
    overrides_data = {}
    overrides = content_tag.get("overrides")
    if overrides:
        try:
            overrides_data = json.loads(overrides)
        except Exception:
            overrides_data = {}
    if not overrides_data.get("allows_year", True):
        year = None
    if not overrides_data.get("allows_lecturer", True):
        lecturer = None

    card_override = overrides_data.get("card")
    item_type_override = overrides_data.get("item_type")
    requires_lecture = bool(overrides_data.get("requires_lecture"))

    conflict = False
    if len(card_ids) > 1 or len(item_type_ids) > 1:
        conflict = True
    card_tag = next(iter(card_ids), None)
    item_type_tag = next(iter(item_type_ids), None)
    if not conflict:
        if card_override is not None and card_tag is not None and card_override != card_tag:
            conflict = True
        elif item_type_override is not None and item_type_tag is not None and item_type_override != item_type_tag:
            conflict = True
        elif ((card_override is not None or card_tag is not None)
              and (item_type_override is not None or item_type_tag is not None)):
            conflict = True

    if conflict:
        result = ParseResult(
            text=message_text,
            group_id=group_id,
            tg_topic_id=tg_topic_id,
            locale=user_locale,
            hashtags=tags or None,
            content_tag=content_tag,
            year=year,
            lecturer=lecturer,
        )
        return result, ParseError("E-ALIAS-CONFLICT")

    item_type_id = item_type_override or item_type_tag
    if item_type_id is not None:
        item = await taxonomy.get_item_type(item_type_id, include_disabled=True)
        if item and item.get("requires_lecture"):
            requires_lecture = True

    if requires_lecture and lecture_no is None:
        result = ParseResult(
            text=message_text,
            group_id=group_id,
            tg_topic_id=tg_topic_id,
            locale=user_locale,
            hashtags=tags or None,
            content_tag=content_tag,
            year=year,
            lecturer=lecturer,
        )
        return result, ParseError("E-NO-SESSION")

    result = ParseResult(
        text=message_text,
        group_id=group_id,
        tg_topic_id=tg_topic_id,
        locale=user_locale,
        hashtags=tags or None,
        content_tag=content_tag,
        year=year,
        lecturer=lecturer,
    )
    return result, None


__all__ = ["parse_message", "ParseResult", "ParseError"]
