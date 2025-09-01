from __future__ import annotations

from math import ceil
from typing import Sequence, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...config import PER_PAGE


def build_children_keyboard(
    children: Sequence[Tuple[str, int | str, str]],
    page: int,
    per_page: int | None = None,
    include_back: bool = True,
    row_width: int = 2,
) -> InlineKeyboardMarkup:
    """Build a paginated inline keyboard for navigation children.

    Parameters
    ----------
    children:
        Sequence of triples ``(kind, id, label)`` describing each child node.
    page:
        One-based page number to render.
    per_page:
        Number of items to show per page.  Defaults to the global
        :data:`PER_PAGE` configuration value when ``None``.
    include_back:
        Whether to include a "back" button at the bottom of the keyboard.
    row_width:
        Maximum number of child buttons to display in each row.
    """

    if per_page is None:
        per_page = PER_PAGE

    total = len(children)
    if per_page <= 0:
        per_page = total or 1
    pages = max(1, ceil(total / per_page))
    page = max(1, min(page, pages))

    start = (page - 1) * per_page
    end = start + per_page

    if row_width <= 0:
        row_width = 1

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for idx, (kind, ident, label) in enumerate(children[start:end], start=1):
        row.append(
            InlineKeyboardButton(text=label, callback_data=f"nav:{kind}:{ident}")
        )
        if idx % row_width == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="◀", callback_data=f"nav:page:{page - 1}")
        )
    if page < pages:
        nav_row.append(
            InlineKeyboardButton(text="▶", callback_data=f"nav:page:{page + 1}")
        )
    if nav_row:
        keyboard.append(nav_row)

    if include_back:
        keyboard.append([InlineKeyboardButton(text="🔙", callback_data="nav:back")])
    return InlineKeyboardMarkup(keyboard)
