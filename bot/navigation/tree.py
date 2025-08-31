from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Awaitable, Callable, Dict, Tuple

from ..db import (
    get_levels,
    get_terms_by_level,
    get_subjects_by_level_and_term,
    get_available_sections_for_subject,
    get_years_for_subject_section,
    get_lecturers_for_subject_section,
    list_lecture_titles,
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
_cache: Dict[Tuple[str, Tuple[Any, ...]], Tuple[float, Any]] = {}


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

    async def children(self) -> Any:
        """Return this node's children using the configured loader.

        Results are cached for ``CACHE_TTL_SECONDS`` seconds to reduce database
        load.  The cache can be cleared via :func:`invalidate`.
        """

        key = (self.kind, self.args)
        now = time.time()
        cached = _cache.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        loader = KIND_TO_LOADER.get(self.kind)
        if loader is None:
            result: Any = []
        else:
            result = await loader(*self.args)

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

__all__ = ["Node", "invalidate", "KIND_TO_LOADER"]
