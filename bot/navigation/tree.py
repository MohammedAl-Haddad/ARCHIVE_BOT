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
    get_lectures_by_lecturer_year,
    list_lecture_titles_by_year,
    list_categories_for_subject_section_year,
    get_types_for_lecture,
    can_view,
    list_term_resource_kinds,
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

TERM_RESOURCE_LABELS = {
    "attendance": "جدول الحضور 🗓️",
    "study_plan": "الخطة الدراسية 📖",
    "channels": "روابط القنوات 📎",
    "outcomes": "مخرجات التعلم 🎯",
    "tips": "نصائح دراسية 💡",
    "projects": "أفكار المشاريع 🛠️",
    "programs": "برامج مقترحة 🖥️",
    "apps": "تطبيقات مفيدة 📱",
    "skills": "مهارات مطلوبة 🧠",
    "forums": "منتديات للنقاش 💬",
    "sites": "مواقع إلكترونية 🌐",
}

YEAR_OPTION_LABELS = {
    "lectures": "المحاضرات 🎓",
    "projects": "المشاريع 🛠️",
    "assignments": "التكاليف 📝",
}

async def get_term_menu_items(level_id: int, term_id: int):
    items = [("subjects", "عرض المواد")]
    kinds = await list_term_resource_kinds(level_id, term_id)
    for kind in kinds:
        label = TERM_RESOURCE_LABELS.get(kind, kind)
        items.append((kind, label))
    return items


async def get_section_menu_items(subject_id: int, section: str):
    """Return filter options for a subject section.

    Currently exposes filtering by year or by lecturer.
    """

    return [("year", "حسب السنة"), ("lecturer", "حسب المحاضر")]


async def get_section_option_children(subject_id: int, section: str, filter_by: str):
    """Return children for a section based on ``filter_by``.

    Depending on the selected filter, dispatches to the appropriate loader
    for years or lecturers.
    """

    if filter_by == "year":
        return await get_years_for_subject_section(subject_id, section)
    if filter_by == "lecturer":
        return await get_lecturers_for_subject_section(subject_id, section)
    return []


async def get_year_menu_items(subject_id: int, section: str, year_id: int):
    """Return available material categories for a given year."""

    items = []
    lectures = await list_lecture_titles_by_year(subject_id, section, year_id)
    if lectures:
        items.append(("lectures", YEAR_OPTION_LABELS["lectures"]))
    categories = await list_categories_for_subject_section_year(
        subject_id, section, year_id
    )
    for cat in categories:
        label = YEAR_OPTION_LABELS.get(cat, cat)
        items.append((cat, label))
    return items


async def get_year_option_children(
    subject_id: int, section: str, year_id: int, option: str
):
    """Return children for a year option."""

    if option == "lectures":
        return await get_lecturers_for_subject_section(subject_id, section)
    return []


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
    "term": "term_option",
    "term_option": "subject",
    "subject": "section",
    "section": "section_option",
    "section_option": "year",
    "year": "year_option",
    "year_option": "lecturer",
    "lecturer": "lecture",
    "lecture": "lecture_type",
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
            if self.kind == "section_option" and len(self.args) >= 3:
                filter_by = self.args[2]
                if filter_by in ("year", "lecturer"):
                    child_kind = filter_by
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
    "term": get_term_menu_items,
    "term_option": get_subjects_by_level_and_term,
    "subject": get_available_sections_for_subject,
    "section": get_section_menu_items,
    "section_option": get_section_option_children,
    "year": get_year_menu_items,
    "year_option": get_year_option_children,
    "lecturer": get_lectures_by_lecturer_year,
    "lecture": get_types_for_lecture,
}


async def get_children(kind: str, id: Any | None = None, user_id: int | None = None) -> Any:
    """Return children for the node specified by ``kind`` and ``id``.

    The function constructs a :class:`Node` instance, associates the
    appropriate loader from :data:`KIND_TO_LOADER` and returns the loader
    result.  ``id`` may be a tuple of identifiers which will be expanded into
    positional arguments for the loader.  Results are cached so repeated calls
    for the same ``kind``/``id`` pair issue at most one database query.
    """

    args = id if isinstance(id, tuple) else (() if id is None else (id,))
    node = Node(kind, args)
    return await node.children(user_id)

__all__ = ["Node", "invalidate", "KIND_TO_LOADER", "get_children"]
