from __future__ import annotations

"""Handlers for exploring the navigation tree via inline keyboards."""

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from ..navigation.nav_stack import NavStack
from ..navigation.tree import get_children, CHILD_KIND
from ..keyboards.builders.paginated import build_children_keyboard


async def _render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    ident: Optional[int | str],
    page: int,
) -> None:
    """Render children for ``kind``/``ident`` at ``page``."""

    user_id = update.effective_user.id if update.effective_user else None
    children_raw = await get_children(kind, ident, user_id)
    child_kind = CHILD_KIND.get(kind, kind)
    children = [
        (
            child_kind,
            item[0] if isinstance(item, (tuple, list)) else item,
            item[1] if isinstance(item, (tuple, list)) else str(item),
        )
        for item in children_raw
    ]

    keyboard = build_children_keyboard(children, page)
    text = NavStack(context.user_data).path_text() or "اختر عنصرًا:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


def _parse_id(value: str) -> int | str:
    return int(value) if value.isdigit() else value


async def _render_current(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1
) -> None:
    stack = NavStack(context.user_data)
    node = stack.peek()
    if node is None:
        kind, ident = "root", None
    else:
        kind, ident, _ = node
    await _render(update, context, kind, ident, page)


async def navtree_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start navigation at the root of the tree."""

    stack = NavStack(context.user_data)
    while stack.pop():
        pass
    await _render(update, context, "root", None, 1)


async def navtree_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unified callback query handler for navigation tree buttons."""

    query = update.callback_query
    data = query.data if query else ""
    stack = NavStack(context.user_data)

    if data == "back":
        stack.pop()
        await _render_current(update, context, 1)
        if query:
            await query.answer()
        return

    if data.startswith("page:"):
        page = int(data.split(":", 1)[1])
        await _render_current(update, context, page)
        if query:
            await query.answer()
        return

    if ":" in data:
        kind, ident_str = data.split(":", 1)
        ident = _parse_id(ident_str)
        parent = stack.peek()
        parent_kind = parent[0] if parent else "root"
        parent_id = parent[1] if parent else None
        user_id = query.from_user.id if query and query.from_user else None
        children_raw = await get_children(parent_kind, parent_id, user_id)
        label = ""
        for item in children_raw:
            item_id = item[0] if isinstance(item, (tuple, list)) else item
            item_label = item[1] if isinstance(item, (tuple, list)) else str(item)
            if str(item_id) == ident_str:
                label = item_label
                break
        stack.push((kind, ident, label))
        await _render(update, context, kind, ident, 1)
        if query:
            await query.answer()
        return

    if query:
        await query.answer()
