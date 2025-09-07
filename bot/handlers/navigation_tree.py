from __future__ import annotations

"""Handlers for exploring the navigation tree via inline keyboards.

Navigation flow: level → term → subject → section → filter (year/lecturer) → ….
"""

from typing import Optional
import time
import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..navigation.nav_stack import NavStack
from ..navigation.tree import (
    get_children,
    CHILD_KIND,
    CACHE_TTL_SECONDS,
    get_latest_material_by_category,
    SECTION_CATEGORY_LABELS,
    CATEGORY_SECTIONS,
)
from ..keyboards.builders.paginated import build_children_keyboard
from ..keyboards.builders.main_menu import build_main_menu
from ..db import (
    is_owner,
    has_perm,
    MANAGE_ADMINS,
    get_latest_term_resource,
    get_types_for_lecture,
    LECTURE_TYPE_LABELS,
    get_materials_by_card,
)
from ..utils.retry import retry

logger = logging.getLogger(__name__)

LAST_CHILDREN_KEY = "last_children"
LAST_CHILDREN_TTL_SECONDS = CACHE_TTL_SECONDS
# Key in ``application.bot_data`` used to invalidate per-user caches.
BUMP_KEY = "navtree_bump"

# Arabic labels with icons for subject sections
SECTION_LABELS = {
    "theory": "نظري 📘",
    "discussion": "مناقشة 💬",
    "lab": "عملي 🔬",
    "field_trip": "رحلة 🚌",
}

# Arabic labels with icons for subject cards
CARD_LABELS = {
    "syllabus": "التوصيف 📄",
    "glossary": "المفردات الدراسية 📖",
    "practical": "الواقع التطبيقي ⚙️",
    "references": "مراجع 📚",
    "skills": "مهارات 🧠",
    "open_source_projects": "مشاريع مفتوحة المصدر 🛠️",
}

# Labels for filter options used when a subject has a single section
FILTER_LABELS = {
    "year": "حسب السنة",
    "lecturer": "حسب المحاضر",
}



async def _load_children(
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    ident: Optional[
        int
        | str
        | tuple[int, int | str]
        | tuple[int, int | str, str]
        | tuple[int, int | str, int, str]
    ],
    user_id: int | None,
):
    """Return children for ``kind``/``ident`` using a short-lived cache."""

    node_key = (kind, ident)
    now = time.time()
    bump = 0
    if getattr(context, "application", None):
        bump = context.application.bot_data.get(BUMP_KEY, 0)
    cached = context.user_data.get(LAST_CHILDREN_KEY)
    if (
        isinstance(cached, dict)
        and cached.get("node_key") == node_key
        and cached.get("bump") == bump
        and now - cached.get("timestamp", 0) < LAST_CHILDREN_TTL_SECONDS
    ):
        return cached["children"]

    children_raw = await retry(get_children, kind, ident, user_id, logger=logger)
    child_kind = CHILD_KIND.get(kind, kind)
    if kind == "section_option" and isinstance(ident, tuple) and len(ident) >= 3:
        filter_by = ident[2]
        if filter_by in ("year", "lecturer"):
            child_kind = filter_by
    children: list = []
    if kind == "lecture" and isinstance(children_raw, dict):
        for cat, entry in children_raw.items():
            if isinstance(entry, (list, tuple)):
                label = entry[1] if len(entry) > 1 else entry[0]
            elif isinstance(entry, dict):
                label = entry.get("label_ar") or entry.get("label_en") or entry.get("title")
            else:
                label = entry
            if not label:
                label = LECTURE_TYPE_LABELS.get(cat, cat)
            children.append((child_kind, cat, label))
    elif kind == "subject" and child_kind == "section" and isinstance(children_raw, list):
        # ``children_raw`` may be in one of two formats:
        #   1. legacy: ["theory", "lab", "syllabus"]
        #   2. new: [("section", "theory", "نظري"), ("card", "syllabus", "التوصيف")]
        sections: list[tuple[str, str]] = []
        cards: list[tuple[str, str]] = []
        if children_raw and all(isinstance(it, (list, tuple)) and len(it) >= 2 for it in children_raw):
            for item in children_raw:
                kind_hint = item[0]
                key = item[1]
                label = item[2] if len(item) > 2 else None
                if label is None:
                    label = SECTION_LABELS.get(key, CARD_LABELS.get(key, str(key)))
                if kind_hint == "section":
                    sections.append((key, label))
                elif kind_hint == "card":
                    cards.append((key, label))
                else:
                    # Fall back to guessing based on known sections
                    if key in SECTION_LABELS:
                        sections.append((key, label))
                    else:
                        cards.append((key, label))
        else:
            # Legacy format: simple list of codes
            sections = [(s, SECTION_LABELS.get(s, s)) for s in SECTION_LABELS if s in children_raw]
            cards = [(c, CARD_LABELS.get(c, c)) for c in CARD_LABELS if c in children_raw]

        if len(sections) > 1:
            for sect, label in sections:
                item_id = f"{ident}:{sect}"
                children.append(("sec", item_id, label))
            for card, label in cards:
                children.append(("card", f"{ident}:{card}", label))
        elif len(sections) == 1:
            sect, _lab = sections[0]
            for filt in ("year", "lecturer"):
                item_id = f"{ident}-{sect}-{filt}"
                children.append(("section_option", item_id, FILTER_LABELS.get(filt, filt)))
            for card, label in cards:
                children.append(("card", f"{ident}:{card}", label))
        else:
            for card, label in cards:
                children.append(("card", f"{ident}:{card}", label))
    else:
        for item in children_raw:
            if (
                kind == "lecturer"
                and child_kind == "lecture"
                and isinstance(item, dict)
            ):
                item_id = item.get("lecture_no")
                item_label = item.get("title", str(item_id))
            elif isinstance(item, (tuple, list)):
                item_id = item[0]
                item_label = item[1] if len(item) > 1 else str(item[0])
            elif isinstance(item, dict):
                item_id = item.get("id") or item.get("key")
                item_label = (
                    item.get("label_ar")
                    or item.get("label_en")
                    or item.get("name")
                    or str(item_id)
                )
            else:
                item_id = item
                item_label = str(item)
            if kind == "level" and child_kind == "term":
                item_id = f"{ident}-{item_id}"
            elif kind == "section" and child_kind == "section_option":
                subj_id, sect = ident if isinstance(ident, tuple) else (ident, None)
                item_id = f"{subj_id}-{sect}-{item_id}"
            elif kind == "section_option" and child_kind in {"year", "lecturer"}:
                subj_id, sect, _filt = ident if isinstance(ident, tuple) else (ident, None, None)
                item_id = f"{subj_id}-{sect}-{item_id}"
            elif kind == "year" and child_kind == "year_option":
                subj_id, sect, year_id = ident if isinstance(ident, tuple) else (ident, None, None)
                item_id = f"{subj_id}-{sect}-{year_id}-{item_id}"
            elif kind == "year_option" and child_kind == "lecturer":
                subj_id, sect, year_id, _opt = (
                    ident if isinstance(ident, tuple) else (ident, None, None, None)
                )
                item_id = f"{subj_id}-{sect}-{item_id}-{year_id}"
            if child_kind == "section":
                item_label = SECTION_LABELS.get(
                    item_label, CARD_LABELS.get(item_label, item_label)
                )
            children.append((child_kind, item_id, item_label))
    context.user_data[LAST_CHILDREN_KEY] = {
        "node_key": node_key,
        "timestamp": now,
        "children": children,
        "bump": bump,
    }
    return children


async def _render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    ident: Optional[
        int
        | str
        | tuple[int, int | str]
        | tuple[int, int | str, str]
        | tuple[int, int | str, int, str]
    ],
    page: int,
    action: str,
) -> None:
    """Render children for ``kind``/``ident`` at ``page`` and log timings."""

    user_id = update.effective_user.id if update.effective_user else None

    db_start = time.perf_counter()
    children = await _load_children(context, kind, ident, user_id)
    db_time = time.perf_counter() - db_start

    render_start = time.perf_counter()
    bump = 0
    if getattr(context, "application", None):
        bump = context.application.bot_data.get(BUMP_KEY, 0)
    stack = NavStack(context.user_data, bump=bump)
    keyboard = build_children_keyboard(children, page, include_back=True)
    text = stack.path_text() or "اختر عنصرًا:"
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
        NavStack(context.user_data, bump=bump).path_text(),
        db_time * 1000,
        render_time * 1000,
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
    bump = 0
    if getattr(context, "application", None):
        bump = context.application.bot_data.get(BUMP_KEY, 0)
    stack = NavStack(context.user_data, bump=bump)
    node = stack.peek()
    if node is None:
        kind, ident = "root", None
    else:
        kind, ident, _ = node
    await _render(update, context, kind, ident, page, action)


async def navtree_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start navigation at the root of the tree."""

    bump = 0
    if getattr(context, "application", None):
        bump = context.application.bot_data.get(BUMP_KEY, 0)
    stack = NavStack(context.user_data, bump=bump)
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
    bump = 0
    if getattr(context, "application", None):
        bump = context.application.bot_data.get(BUMP_KEY, 0)
    stack = NavStack(context.user_data, bump=bump)

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
            await _render_current(update, context, 1, action="pop")
            if query:
                await query.answer()
        except Exception:
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
                        target_chat = (
                            query.message.chat_id if query else update.effective_chat.id
                        )
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
                    "المادة غير متاحة بعد.",
                )
        except Exception:
            await (query.message if query else update.message).reply_text(
                "عذرًا، تعذر جلب المادة.",
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
        if kind == "section_option":
            subj_id = sect = cat = None
            if isinstance(ident, tuple) and len(ident) >= 3:
                subj_id, sect, cat = ident
            if cat in CATEGORY_SECTIONS:
                try:
                    res = await get_latest_material_by_category(subj_id, sect, cat)
                    if res:
                        chat_id, msg_id, url = res
                        if chat_id and msg_id:
                            target_chat = (
                                query.message.chat_id
                                if query
                                else update.effective_chat.id
                            )
                            thread_id = (
                                query.message.message_thread_id
                                if query and query.message
                                else None
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
                                "المادة غير متاحة بعد.",
                            )
                    else:
                        await (query.message if query else update.message).reply_text(
                            "المادة غير متاحة بعد.",
                        )
                except Exception:
                    await (query.message if query else update.message).reply_text(
                        "عذرًا، تعذر جلب المادة.",
                    )
                    logger.exception("Error sending category material")
                if query:
                    await query.answer()
                return
        if kind == "lecture_type":
            parent = stack.peek()
            subj_id = sect = year_id = None
            lecture_title = ""
            if parent and parent[0] == "lecture" and isinstance(parent[1], tuple):
                subj_id, sect, year_id, lecture_title = parent[1]
            try:
                types = await get_types_for_lecture(subj_id, sect, year_id, lecture_title)
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
        if kind == "lecture" and isinstance(ident, int):
            parent = stack.peek()
            subj_id = sect = year_id = None
            if parent and parent[0] == "lecturer" and isinstance(parent[1], tuple):
                subj_id, sect, _lect_id, year_id = parent[1]
            lecture_title = f"محاضرة {ident}: {label}"
            ident = (subj_id, sect, year_id, lecture_title)
        stack.push((kind, ident, label))
        # Auto-skip for single-section subjects is disabled to always show the
        # first-level menu.
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
