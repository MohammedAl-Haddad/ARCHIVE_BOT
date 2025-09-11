from __future__ import annotations

"""Handlers for exploring the navigation tree via inline keyboards.

Navigation flow: subject → section → year/lecturer → lecture → lecture type.
"""

from typing import Optional, Tuple
import time
import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..navigation import NavStack, Node
from ..navigation.nav_builder import build_menu
from ..navigation.tree import (
    get_latest_material_by_category,
    CATEGORY_SECTIONS,
)
from ..keyboards.builders.main_menu import build_main_menu
from ..db import (
    is_owner,
    has_perm,
    MANAGE_ADMINS,
    get_latest_term_resource,
    get_types_for_lecture,
    get_materials_by_card,
)

logger = logging.getLogger(__name__)


def _extract_state(
    stack: NavStack,
) -> Tuple[Optional[int], Optional[str], Optional[int], Optional[int], Optional[int]]:
    subject_id = section_id = year_id = lecturer_id = lecture_no = None
    for node in stack.state():
        if node.kind == "subject":
            subject_id = node.ident
        elif node.kind == "section":
            section_id = node.ident
        elif node.kind == "year":
            year_id = node.ident
        elif node.kind == "lecturer":
            lecturer_id = node.ident
        elif node.kind == "lecture":
            lecture_no = node.ident
    return subject_id, section_id, year_id, lecturer_id, lecture_no


async def _render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int,
    action: str,
) -> None:
    """Render current navigation state using :func:`build_menu`."""

    user_id = update.effective_user.id if update.effective_user else 0
    user_locale = getattr(update.effective_user, "language_code", None) or "ar"
    stack = NavStack(context.user_data)
    subject_id, section_id, year_id, lecturer_id, lecture_no = _extract_state(stack)
    if subject_id is None:
        return

    db_start = time.perf_counter()
    menu = build_menu(
        user_id,
        subject_id,
        section_id,
        year_id,
        lecturer_id,
        lecture_no,
        page=page,
        locale=user_locale,
    )
    db_time = time.perf_counter() - db_start

    text = stack.path_text() or "اختر عنصرًا:"
    keyboard = menu.keyboard

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
        "%s path='%s' db_time=%.3fms message_edit_time=%.3fms",
        action,
        stack.path_text(),
        db_time * 1000,
        message_edit_time * 1000,
    )


def _parse_id(value: str) -> int | tuple[int, int | str] | tuple[int, int | str, str] | str:
    parts = value.replace(":", "-").split("-")
    parsed = [int(p) if p.isdigit() else p for p in parts]
    if len(parsed) == 1:
        return parsed[0]
    return tuple(parsed)


async def _render_current(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1, action: str = "selection"
) -> None:
    await _render(update, context, page, action)


async def navtree_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start navigation at the root of the tree."""

    stack = NavStack(context.user_data)
    while stack.pop():
        pass
    try:
        await _render(update, context, 1, action="selection")
    except Exception:
        await update.effective_message.reply_text(
            "عذرًا، حدث خطأ. حاول مرة أخرى لاحقًا."
        )
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
                    "عذرًا، حدث خطأ أثناء الرجوع للقائمة الرئيسية."
                )
                logger.exception("Error returning to main menu")
            return
        try:
            await _render_current(update, context, 1, action="pop")
            if query:
                await query.answer()
        except Exception:
            if popped:
                stack.push(popped)
            await (query.message if query else update.message).reply_text(
                "عذرًا، حدث خطأ وتم الرجوع للمستوى السابق."
            )
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
                "عذرًا، تعذر عرض الصفحة المطلوبة."
            )
            logger.exception("Error during page selection")
        return

    if data.startswith("card:"):
        ident_str = data.split(":", 1)[1]
        try:
            subj_part, card_code = ident_str.split(":", 1)
            subj_id = int(subj_part)
        except Exception:
            subj_id = None
            card_code = ""
        try:
            mats = await get_materials_by_card(subj_id, card_code)
            if mats:
                for _mid, _title, url, chat_id, msg_id in mats:
                    if chat_id and msg_id:
                        target_chat = query.message.chat_id if query else update.effective_chat.id
                        thread_id = (
                            query.message.message_thread_id if query and query.message else None
                        )
                        await context.bot.copy_message(
                            chat_id=target_chat,
                            from_chat_id=chat_id,
                            message_id=msg_id,
                            message_thread_id=thread_id,
                        )
                    elif url:
                        await (query.message if query else update.message).reply_text(url)
            else:
                await (query.message if query else update.message).reply_text(
                    "المادة غير متاحة بعد."
                )
        except Exception:
            await (query.message if query else update.message).reply_text(
                "عذرًا، تعذر جلب المادة."
            )
            logger.exception("Error sending card material")
        if query:
            await query.answer()
        return

    if data.startswith("sec:"):
        data = f"section:{data.split(':', 1)[1]}"

    if ":" in data:
        kind, ident_str = data.split(":", 1)
        ident = _parse_id(ident_str)

        user_id = query.from_user.id if query and query.from_user else 0
        user_locale = (
            query.from_user.language_code
            if query and query.from_user and getattr(query.from_user, "language_code", None)
            else getattr(update.effective_user, "language_code", None)
        )

        subj_id, sect_id, year_id, lect_id, lect_no = _extract_state(stack)
        menu = build_menu(
            user_id,
            subj_id,
            sect_id,
            year_id,
            lect_id,
            lect_no,
            page=1,
            locale=user_locale or "ar",
        )

        label = ""
        for btn_kind, item_id, item_label in menu.buttons:
            if btn_kind == kind and str(item_id) == ident_str:
                label = item_label
                break

        if kind == "section_option" and ident in CATEGORY_SECTIONS:
            cat = ident
            try:
                res = await get_latest_material_by_category(subj_id, sect_id, cat)
                if res:
                    chat_id, msg_id, url = res
                    if chat_id and msg_id:
                        target_chat = query.message.chat_id if query else update.effective_chat.id
                        thread_id = (
                            query.message.message_thread_id if query and query.message else None
                        )
                        await context.bot.copy_message(
                            chat_id=target_chat,
                            from_chat_id=chat_id,
                            message_id=msg_id,
                            message_thread_id=thread_id,
                        )
                    elif url:
                        await (query.message if query else update.message).reply_text(url)
                    else:
                        await (query.message if query else update.message).reply_text(
                            "المادة غير متاحة بعد."
                        )
                else:
                    await (query.message if query else update.message).reply_text(
                        "المادة غير متاحة بعد."
                    )
            except Exception:
                await (query.message if query else update.message).reply_text(
                    "عذرًا، تعذر جلب المادة."
                )
                logger.exception("Error sending category material")
            if query:
                await query.answer()
            return

        if kind == "lecture_type":
            subj_val, sect_val, year_val, lecture_title = subj_id, sect_id, year_id, ""
            top = stack.peek()
            if top and top.kind == "lecture" and isinstance(top.ident, tuple):
                subj_val, sect_val, year_val, lecture_title = top.ident
            try:
                types = await get_types_for_lecture(subj_val, sect_val, year_val, lecture_title)
                info = types.get(ident)
                if info:
                    _id, url, chat_id, msg_id = info
                    if chat_id and msg_id:
                        target_chat = query.message.chat_id if query else update.effective_chat.id
                        thread_id = (
                            query.message.message_thread_id if query and query.message else None
                        )
                        await context.bot.copy_message(
                            chat_id=target_chat,
                            from_chat_id=chat_id,
                            message_id=msg_id,
                            message_thread_id=thread_id,
                        )
                    elif url:
                        await (query.message if query else update.message).reply_text(url)
                    else:
                        await (query.message if query else update.message).reply_text(
                            "المادة غير متاحة بعد."
                        )
                else:
                    await (query.message if query else update.message).reply_text(
                        "المادة غير متاحة بعد."
                    )
            except Exception:
                await (query.message if query else update.message).reply_text(
                    "عذرًا، تعذر جلب المادة."
                )
                logger.exception("Error sending lecture material")
            if query:
                await query.answer()
            return

        if kind == "term_option":
            if ident_str != "subjects":
                level_id = term_id = None
                try:
                    res = await get_latest_term_resource(level_id, term_id, ident_str)
                    if res:
                        chat_id, msg_id = res
                        target_chat = query.message.chat_id if query else update.effective_chat.id
                        thread_id = (
                            query.message.message_thread_id if query and query.message else None
                        )
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
            ident = None

        if kind == "lecture" and isinstance(ident, int):
            lecture_title = label
            ident = (subj_id, sect_id, year_id, lecture_title)

        stack.push(Node(kind, ident, label))
        try:
            await _render(update, context, 1, action="push")
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

