from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..repo import RepoNotFound, hashtags, linking
from .caption_parser import ParseError


@dataclass
class ContextResult:
    """Binding information resolved from topic or hashtags."""

    subject_id: int
    section_id: Optional[int]
    source: str


async def parse_context(
    group_id: int,
    tg_topic_id: Optional[int],
    tags: List[str],
) -> Tuple[Optional[ContextResult], Optional[ParseError]]:
    """Resolve subject/section context for a message.

    If *tg_topic_id* is provided, the binding is retrieved via
    :func:`linking.get_binding_by_topic` and ``source`` is set to ``'topic'``.
    Otherwise, hashtags are inspected to locate both a subject and section tag
    from :mod:`hashtag_mappings`.  When either tag is missing, a
    ``ParseError('E-NO-CONTEXT')`` is returned.
    """

    if tg_topic_id is not None:
        try:
            binding = await linking.get_binding_by_topic(group_id, tg_topic_id)
        except RepoNotFound:
            return None, ParseError("E-NO-CONTEXT")
        return (
            ContextResult(
                subject_id=binding["subject_id"],
                section_id=binding.get("section_id"),
                source="topic",
            ),
            None,
        )

    subject_id: Optional[int] = None
    section_id: Optional[int] = None
    for raw in tags:
        token = raw.split()[0].lstrip("#")
        mappings = await hashtags.lookup_targets(token)
        for kind, ident in mappings:
            if kind == "subject" and subject_id is None:
                subject_id = ident
            elif kind == "section" and section_id is None:
                section_id = ident
        if subject_id is not None and section_id is not None:
            break

    if subject_id is None or section_id is None:
        return None, ParseError("E-NO-CONTEXT")

    return (
        ContextResult(
            subject_id=subject_id,
            section_id=section_id,
            source="hashtags",
        ),
        None,
    )


__all__ = ["parse_context", "ContextResult", "ParseError"]
