from __future__ import annotations

"""Caption parsing utilities.

This module exposes a single public interface :func:`parse_message` which is
used by other parts of the bot to extract information from a message caption or
body.  The actual parsing logic will be implemented in subsequent iterations;
for now the function simply wraps the provided values in lightweight data
containers so the rest of the codebase can interact with a stable API.
"""

from dataclasses import dataclass
import re
from typing import List, Optional, Tuple

from ..repo import RepoNotFound, hashtags

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
    seen: set[str] = set()
    tags: List[dict] = []
    for tag in HASHTAG_RE.findall(clean_text):
        normalized = hashtags.normalize_alias(tag)
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            resolved = await hashtags.resolve_content_tag(normalized)
        except RepoNotFound:
            result = ParseResult(
                text=message_text,
                group_id=group_id,
                tg_topic_id=tg_topic_id,
                locale=user_locale,
                hashtags=None,
            )
            return result, ParseError("E-HT-UNKNOWN")
        tags.append(resolved)

    result = ParseResult(
        text=message_text,
        group_id=group_id,
        tg_topic_id=tg_topic_id,
        locale=user_locale,
        hashtags=tags or None,
    )
    return result, None


__all__ = ["parse_message", "ParseResult", "ParseError"]
