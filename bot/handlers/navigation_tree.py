from __future__ import annotations

"""Handlers for exploring the navigation tree via inline keyboards."""

from typing import Optional
import time
import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..navigation.nav_stack import NavStack
from ..navigation.tree import get_children, CHILD_KIND, CACHE_TTL_SECONDS
from ..keyboards.builders.paginated import build_children_keyboard
from ..keyboards.builders.main_menu import build_main_menu
from ..db import is_owner, has_perm, MANAGE_ADMINS, get_latest_term_resource
from ..utils.retry import retry

logger = logging.getLogger(__name__)

LAST_CHILDREN_KEY = "last_children"
LAST_CHILDREN_TTL_SECONDS = CACHE_TTL_SECONDS


async def _load_children(
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    ident: Optional[int | str | tuple[int, int | str]],
    user_id: int | None,
):
    """Return children for ``kind``/``ident`` using a short-lived cache."""

    node_key = (kind, ident)
    now = time.time()
    cached = context.user_data.get(LAST_CHILDREN_KEY)
    if (
        isinstance(cached, dict)
        and cached.get("node_key") == node_key
        and now - cached.get("timestamp", 0) < LAST_CHILDREN_TTL_SECONDS
    ):
        return cached["children"]

    children_raw = await retry(get_children, kind, ident, user_id, logger=logger)
    child_kind = CHILD_KIND.get(kind, kind)
    children = []
    for item in children_raw:
        if isinstance(item, (tuple, list)):
            item_id = item[0]
            item_label = item[1] if len(item) > 1 else str(item[0])
        else:
            item_id = item
            item_label = str(item)
        if kind == "level" and child_kind == "term":
            item_id = f"{ident}-{item_id}"
        elif kind == "subject" and child_kind == "section":
            item_id = f"{ident}-{item_id}"
        children.append((child_kind, item_id, item_label))
    context.user_data[LAST_CHILDREN_KEY] = {
        "node_key": node_key,
        "timestamp": now,
        "children": children,
    }
    return children


async def _render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    ident: Optional[int | str | tuple[int, int | str]],
    page: int,
    action: str,
) -> None:
    """Render children for ``kind``/``ident`` at ``page`` and log timings."""

    user_id = update.effective_user.id if update.effective_user else None

    db_start = time.perf_counter()
    children = await _load_children(context, kind, ident, user_id)
    db_time = time.perf_counter() - db_start

    render_start = time.perf_counter()
    include_back = True
    keyboard = build_children_keyboard(children, page, include_back=include_back)
    text = NavStack(context.user_data).path_text() or "اختر عنصرًا:"
    render_time = time.perf_counter() - render_start

    if update.callback_query:
        await update.callback_query.answer()

    message_start = time.perf_counter()
    if update.callback_query:
        current = update.callback_query.message
        if current and current.text == text and current.reply_markup == keyboard:
            return
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest as err:
            if "Message is not modified" not in err.message:
                raise
            return
    else:
        await update.message.reply_text(text, reply_markup=keyboard)
    message_edit_time = time.perf_counter() - message_start

    logger.info(
        "%s path='%s' db_time=%.3fms render_time=%.3fms message_edit_time=%.3fms",
        action,
        NavStack(context.user_data).path_text(),
        db_time * 1000,
        render_time * 1000,
        message_edit_time * 1000,
    )


def _parse_id(value: str) -> int | tuple[int, int | str] | str:
    if "-" in value:
        a, b = value.split("-", 1)
        a_val = int(a) if a.isdigit() else a
        b_val = int(b) if b.isdigit() else b
        return a_val, b_val
    return int(value) if value.isdigit() else value


async def _render_current(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1, action: str = "selection"
) -> None:
    stack = NavStack(context.user_data)
    node = stack.peek()
    if node is None:
        kind, ident = "root", None
    else:
        kind, ident, _ = node
    await _render(update, context, kind, ident, page, action)


async def navtree_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start navigation at the root of the tree."""

    stack = NavStack(context.user_data)
    while stack.pop():
        pass
    try:
        await _render(update, context, "root", None, 1, action="selection")
    except Exception:
        await update.effective_message.reply_text(
            "عذرًا، حدث خطأ. حاول مرة أخرى لاحقًا.")
        logger.exception("navtree_start failed")


async def navtree_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unified callback query handler for navigation tree buttons."""

    query = update.callback_query
    data = query.data if query else ""
    if data.startswith("nav:"):
        data = data[4:]
    stack = NavStack(context.user_data)

    if data == "back":
        popped = stack.pop()
        if not popped:
            try:
                user = query.from_user if query else update.effective_user
                is_admin = False
                if user:
                    is_admin = is_owner(user.id) or await has_perm(user.id, MANAGE_ADMINS)
                if query:
                    await query.edit_message_text(
                        "اختر من القائمة:", reply_markup=build_main_menu(is_admin)
                    )
                    await query.answer()
                else:
                    await update.effective_message.reply_text(
                        "اختر من القائمة:", reply_markup=build_main_menu(is_admin)
                    )
            except Exception:
                await (query.message if query else update.message).reply_text(
                    "عذرًا، حدث خطأ أثناء الرجوع للقائمة الرئيسية.")
                logger.exception("Error returning to main menu")
            return
        try:
            popped_subject = None
            if popped and popped[0] == "section":
                parent = stack.peek()
                if parent and parent[0] == "subject":
                    user_id = None
                    if query and query.from_user:
                        user_id = query.from_user.id
                    elif update.effective_user:
                        user_id = update.effective_user.id
                    try:
                        children = await _load_children(
                            context, "subject", parent[1], user_id
                        )
                    except Exception:
                        children = None
                    if children is not None and len(children) == 1:
                        popped_subject = stack.pop()

            await _render_current(update, context, 1, action="pop")
            if query:
                await query.answer()
        except Exception:
            if popped_subject:
                stack.push(popped_subject)
            if popped:
                stack.push(popped)
            await (query.message if query else update.message).reply_text(
                "عذرًا، حدث خطأ وتم الرجوع للمستوى السابق.")
            logger.exception("Error during pop")
        return

    if data.startswith("page:"):
        page = int(data.split(":", 1)[1])
        try:
            await _render_current(update, context, page, action="selection")
            if query:
                await query.answer()
        except Exception:
            await (query.message if query else update.message).reply_text(
                "عذرًا، تعذر عرض الصفحة المطلوبة.")
            logger.exception("Error during page selection")
        return

    if ":" in data:
        kind, ident_str = data.split(":", 1)
        ident = _parse_id(ident_str)
        parent = stack.peek()
        parent_kind = parent[0] if parent else "root"
        parent_id = parent[1] if parent else None
        user_id = query.from_user.id if query and query.from_user else None
        try:
            children = await _load_children(context, parent_kind, parent_id, user_id)
        except Exception:
            await (query.message if query else update.message).reply_text(
                "عذرًا، حدث خطأ أثناء جلب البيانات.")
            logger.exception("Error loading children for selection")
            return
        label = ""
        for _, item_id, item_label in children:
            if str(item_id) == ident_str:
                label = item_label
                break
        if kind == "term_option":
            if ident_str != "subjects":
                level_id, term_id = (
                    parent_id if isinstance(parent_id, tuple) else (None, parent_id)
                )
                try:
                    res = await get_latest_term_resource(level_id, term_id, ident_str)
                    if res:
                        chat_id, msg_id = res
                        target_chat = query.message.chat_id if query else update.effective_chat.id
                        thread_id = None
                        if query and query.message:
                            thread_id = query.message.message_thread_id
                        await context.bot.copy_message(
                            chat_id=target_chat,
                            from_chat_id=chat_id,
                            message_id=msg_id,
                            message_thread_id=thread_id,
                        )
                    else:
                        await (query.message if query else update.message).reply_text(
                            "المورد غير متاح بعد."
                        )
                except Exception:
                    await (query.message if query else update.message).reply_text(
                        "عذرًا، تعذر جلب المورد."
                    )
                    logger.exception("Error sending term resource")
                if query:
                    await query.answer()
                return
            ident = parent_id
        stack.push((kind, ident, label))
        if kind == "subject":
            try:
                sections = await _load_children(context, kind, ident, user_id)
            except Exception:
                stack.pop()
                await (query.message if query else update.message).reply_text(
                    "عذرًا، حدث خطأ أثناء جلب الأقسام."
                )
                logger.exception("Error loading sections for subject")
                return
            if len(sections) == 1:
                section_kind, section_id, section_label = sections[0]
                section_ident = _parse_id(str(section_id))
                stack.push((section_kind, section_ident, section_label))
                try:
                    await _render(update, context, section_kind, section_ident, 1, action="push")
                    if query:
                        await query.answer()
                except Exception:
                    stack.pop()
                    stack.pop()
                    await (query.message if query else update.message).reply_text(
                        "عذرًا، تعذر تحميل العنصر. تم الرجوع للمستوى السابق."
                    )
                    logger.exception("Error during push selection")
                return
        try:
            await _render(update, context, kind, ident, 1, action="push")
            if query:
                await query.answer()
        except Exception:
            stack.pop()
            await (query.message if query else update.message).reply_text(
                "عذرًا، تعذر تحميل العنصر. تم الرجوع للمستوى السابق."
            )
            logger.exception("Error during push selection")
        return

    if query:
        try:
            await query.answer()
        except Exception:
            logger.exception("Error answering callback query")
