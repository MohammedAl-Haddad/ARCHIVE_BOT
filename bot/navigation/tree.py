from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Awaitable, Callable, Dict, Tuple, Optional

from ..db import (
    get_levels,
    get_terms_by_level,
    get_subjects_by_level_and_term,
    get_available_sections_for_subject,
    get_years_for_subject_section,
    get_lecturers_for_subject_section,
    list_lecture_titles,
    can_view,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Results from DB loaders are cached for a short period to avoid hitting the
# database on every navigation.  The TTL is intentionally short (90 seconds)
# so that administrative updates become visible quickly while still cutting
# down on repeated queries.
CACHE_TTL_SECONDS = 90  # within the 60-120 second range requested

# cache key -> (timestamp, value)
_cache: Dict[Tuple[int | None, str, Tuple[Any, ...]], Tuple[float, Any]] = {}


def invalidate() -> None:
    """Clear the cached results.

    This should be called after administrative updates that might change the
    structure of the navigation tree so subsequent requests fetch fresh data
    from the database.
    """

    _cache.clear()


# ---------------------------------------------------------------------------
# Node abstraction
# ---------------------------------------------------------------------------
Loader = Callable[..., Awaitable[Any]]

# Mapping from a parent node kind to the kind of its children.  Used for
# permission checks.
CHILD_KIND: Dict[str, str] = {
    "root": "level",
    "level": "term",
    "term": "subject",
    "subject": "section",
    "section": "year",
    "year": "lecturer",
    "lecturer": "lecture",
}


@dataclass
class Node:
    """A node in the navigation tree.

    Parameters
    ----------
    kind:
        The type of the current node (e.g. ``"level"`` or ``"subject"``).
    args:
        Positional arguments passed to the loader associated with ``kind``.
        These typically include identifiers required to fetch child nodes.
    label:
        Optional human readable label for this node.
    """

    kind: str
    args: Tuple[Any, ...] = field(default_factory=tuple)
    label: str = ""
    loader: Optional[Loader] = None

    def __post_init__(self) -> None:
        if self.loader is None:
            self.loader = KIND_TO_LOADER.get(self.kind)

    async def children(self, user_id: int | None = None) -> Any:
        """Return this node's children using the configured loader.

        Results are cached for ``CACHE_TTL_SECONDS`` seconds to reduce database
        load.  The cache can be cleared via :func:`invalidate`.
        """

        key = (user_id, self.kind, self.args)
        now = time.time()
        cached = _cache.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        loader = self.loader
        if loader is None:
            result: Any = []
        else:
            result = await loader(*self.args)

            child_kind = CHILD_KIND.get(self.kind, self.kind)
            if isinstance(result, list):
                filtered = []
                for item in result:
                    item_id = item[0] if isinstance(item, (list, tuple)) else item
                    if await can_view(user_id, child_kind, item_id):
                        filtered.append(item)
                result = filtered

        _cache[key] = (now, result)
        return result


# ---------------------------------------------------------------------------
# Mapping of node kinds to loader functions
# ---------------------------------------------------------------------------
KIND_TO_LOADER: Dict[str, Loader] = {
    "root": get_levels,  # top-level -> levels
    "level": get_terms_by_level,
    "term": get_subjects_by_level_and_term,
    "subject": get_available_sections_for_subject,
    "section": get_years_for_subject_section,
    "year": get_lecturers_for_subject_section,
    "lecturer": list_lecture_titles,
}


async def get_children(kind: str, id: Any | None = None, user_id: int | None = None) -> Any:
    """Return children for the node specified by ``kind`` and ``id``.

    The function constructs a :class:`Node` instance, associates the
    appropriate loader from :data:`KIND_TO_LOADER` and returns the loader
    result.  Results are cached so repeated calls for the same ``kind``/``id``
    pair issue at most one database query.
    """

    args = () if id is None else (id,)
    node = Node(kind, args)
    return await node.children(user_id)

__all__ = ["Node", "invalidate", "KIND_TO_LOADER", "get_children"]
