from __future__ import annotations

"""Caption parsing utilities.

This module exposes a single public interface :func:`parse_message` which is
used by other parts of the bot to extract information from a message caption or
body.  The actual parsing logic will be implemented in subsequent iterations;
for now the function simply wraps the provided values in lightweight data
containers so the rest of the codebase can interact with a stable API.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ParseResult:
    """Result of a successful parsing operation."""

    text: str
    group_id: Optional[int] = None
    tg_topic_id: Optional[int] = None
    locale: Optional[str] = None
    hashtags: Optional[List[str]] = None


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

    This is a placeholder implementation that simply returns the input wrapped
    in :class:`ParseResult` with ``error`` set to ``None``.  It establishes a
    consistent interface for future, more sophisticated caption parsing logic.
    """

    result = ParseResult(
        text=message_text,
        group_id=group_id,
        tg_topic_id=tg_topic_id,
        locale=user_locale,
        hashtags=None,
    )
    return result, None


__all__ = ["parse_message", "ParseResult", "ParseError"]
