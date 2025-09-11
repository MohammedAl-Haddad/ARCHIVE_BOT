from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from math import ceil
from typing import Any, Dict, List, Tuple

from telegram import InlineKeyboardMarkup

from ..config import PER_PAGE as CONFIG_PER_PAGE
from ..keyboards.builders import build_children_keyboard
from .tree import CHILD_KIND, get_children

# ---------------------------------------------------------------------------
# Public constants and type aliases
# ---------------------------------------------------------------------------
# Expose ``PER_PAGE`` similar to other modules.  It can be overridden when
# calling :func:`build_menu` if needed by tests or handlers.
PER_PAGE = CONFIG_PER_PAGE

# Button representation used by :class:`Menu`.  Each entry mirrors the structure
# used by the navigation tree: ``(kind, identifier, label)``.
Button = Tuple[str, str, str]


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class Menu:
    """Container returned by :func:`build_menu`.

    Attributes
    ----------
    buttons:
        List of ``Button`` tuples representing the current page items.
    page:
        Current one-based page number.
    pages:
        Total number of pages available.
    keyboard:
        Inline keyboard markup generated for the menu.
    has_back:
        Whether a "back" button was included in ``keyboard``.
    """

    buttons: List[Button]
    page: int
    pages: int
    keyboard: InlineKeyboardMarkup
    has_back: bool = False


# ---------------------------------------------------------------------------
# Simple cache handling
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 90
# cache key -> (timestamp, Menu)
_cache: Dict[Tuple[Any, ...], Tuple[float, Menu]] = {}


def invalidate() -> None:
    """Clear cached menus."""

    _cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _load_children(kind: str, ident: Any, user_id: int | None) -> List[Button]:
    """Return children for ``kind``/``ident`` converted to ``Button`` tuples."""

    raw = await get_children(kind, ident, user_id)
    child_kind = CHILD_KIND.get(kind, kind)

    buttons: List[Button] = []

    if isinstance(raw, dict):
        for key, val in raw.items():
            label = str(val)
            if isinstance(val, (tuple, list)) and len(val) > 1:
                label = str(val[1])
            buttons.append((child_kind, str(key), label))
        return buttons

    for item in raw or []:
        if isinstance(item, dict):
            ident_val = (
                item.get("id")
                or item.get("lecture_no")
                or item.get("code")
                or item.get("value")
            )
            label = item.get("label") or item.get("name") or item.get("title")
            if label is None:
                label = str(ident_val)
        elif isinstance(item, (tuple, list)) and item:
            ident_val = item[0]
            label = item[1] if len(item) > 1 else str(item[0])
        else:
            ident_val = item
            label = str(item)
        buttons.append((child_kind, str(ident_val), str(label)))
    return buttons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_menu(
    user_id: int,
    subject_id: int,
    section_id: str | None = None,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    lecture_no: int | None = None,
    *,
    page: int = 1,
    locale: str = "ar",
) -> Menu:
    """Build a navigation menu for the given parameters.

    Parameters
    ----------
    user_id:
        Identifier of the requesting user; used for permission aware loaders.
    subject_id:
        Current subject identifier.
    section_id, year_id, lecturer_id, lecture_no:
        Optional identifiers representing the current navigation depth.
    page:
        One-based page number to render.
    locale:
        Language code affecting lecture title guesses when needed.
    """

    key = (user_id, subject_id, section_id, year_id, lecturer_id, lecture_no, page, locale)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    async def _build() -> Menu:
        # Determine the node kind and identifier expected by the navigation tree.
        if section_id is None:
            kind = "subject"
            ident = subject_id
        elif year_id is None and lecturer_id is None and lecture_no is None:
            kind = "section"
            ident = (subject_id, section_id)
        elif year_id is not None and lecturer_id is None and lecture_no is None:
            kind = "year"
            ident = (subject_id, section_id, year_id)
        elif year_id is not None and lecturer_id is not None and lecture_no is None:
            kind = "lecturer"
            ident = (subject_id, section_id, lecturer_id, year_id)
        elif (
            year_id is not None
            and lecturer_id is not None
            and lecture_no is not None
        ):
            prefix = "Lecture" if locale.startswith("en") else "محاضرة"
            title = f"{prefix} {lecture_no}"
            kind = "lecture"
            ident = (subject_id, section_id, year_id, title)
        else:
            kind = "section"
            ident = (subject_id, section_id)

        buttons = await _load_children(kind, ident, user_id)

        per_page = PER_PAGE
        total = len(buttons)
        pages = max(1, ceil(total / per_page)) if per_page > 0 else 1
        current_page = max(1, min(page, pages))
        include_back = section_id is not None or year_id is not None or lecturer_id is not None or lecture_no is not None
        keyboard = build_children_keyboard(
            buttons, current_page, per_page=per_page, include_back=include_back
        )
        return Menu(buttons, current_page, pages, keyboard, include_back)

    menu = asyncio.run(_build())
    _cache[key] = (now, menu)
    return menu


__all__ = ["Menu", "build_menu", "invalidate", "PER_PAGE"]
