import os
import asyncio
import aiosqlite
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.db import base as db_base
from bot.db import subjects, materials, rbac
from bot.navigation.nav_stack import NavStack, Node


CATEGORIES = [
    ("syllabus", "التوصيف 📄"),
    ("glossary", "المفردات الدراسية 📖"),
    ("practical", "الواقع التطبيقي ⚙️"),
    ("references", "مراجع 📚"),
    ("skills", "مهارات 🧠"),
    ("open_source_projects", "مشاريع مفتوحة المصدر 🛠️"),
]


class DummyMessage:
    def __init__(self):
        self.sent = []
        self.chat_id = 100
        self.message_thread_id = 200
        self.text = ""
        self.reply_markup = None

    async def reply_text(self, text, reply_markup=None):
        self.text = text
        self.reply_markup = reply_markup
        self.sent.append((text, reply_markup))

    async def edit_message_text(self, text, reply_markup=None):
        self.text = text
        self.reply_markup = reply_markup
        self.sent.append((text, reply_markup))

def _setup_db(tmp_path, with_lab=False):
    async def inner():
        db_path = tmp_path / "test.db"
        db_base.DB_PATH = subjects.DB_PATH = materials.DB_PATH = rbac.DB_PATH = str(db_path)
        await db_base.init_db()
        async with aiosqlite.connect(db_base.DB_PATH) as db:
            await db.execute("INSERT INTO levels (name) VALUES ('L1')")
            await db.execute("INSERT INTO terms (name) VALUES ('T1')")
            await db.execute(
                "INSERT INTO subjects (code, name, level_id, term_id) VALUES ('S1','Sub1',1,1)"
            )
            await db.commit()
        await materials.insert_material(
            1, "theory", "lecture", "t", tg_storage_chat_id=1, tg_storage_msg_id=11
        )
        if with_lab:
            await materials.insert_material(
                1, "lab", "lecture", "l", tg_storage_chat_id=1, tg_storage_msg_id=12
            )
        for i, (cat, _label) in enumerate(CATEGORIES):
            await materials.insert_material(
                1,
                "theory",
                cat,
                f"{cat} title",
                tg_storage_chat_id=10 + i,
                tg_storage_msg_id=100 + i,
            )
    asyncio.run(inner())


def _build_initial_stack(ctx):
    stack = NavStack(ctx.user_data)
    stack.push(Node("level", 1, "L1"))
    stack.push(Node("term", (1, 1), "T1"))
    stack.push(Node("term_option", (1, 1), "عرض المواد"))
    return stack


def test_single_section_does_not_skip(tmp_path):
    _setup_db(tmp_path, with_lab=False)
    navtree = import_module("bot.handlers.navigation_tree")
    from bot.navigation.tree import invalidate
    invalidate()
    ctx = SimpleNamespace(user_data={})
    _build_initial_stack(ctx)

    message = DummyMessage()
    query = SimpleNamespace(
        data="subject:1",
        message=message,
        answer=AsyncMock(),
        from_user=None,
        edit_message_text=message.edit_message_text,
    )
    update = SimpleNamespace(callback_query=query, effective_user=None)
    context = SimpleNamespace(
        user_data=ctx.user_data,
        bot=SimpleNamespace(copy_message=AsyncMock()),
    )

    asyncio.run(navtree.navtree_callback(update, context))

    stack = NavStack(ctx.user_data)
    assert stack.peek() and stack.peek().kind == "subject"

    keyboard = message.sent[-1][1]
    buttons = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "nav:section_option:1-theory-year" in buttons
    assert "nav:section_option:1-theory-lecturer" in buttons
    assert "nav:sec:1:theory" not in buttons
    for cat, _label in CATEGORIES:
        assert f"nav:card:1:{cat}" in buttons


def test_multiple_sections_no_skip_and_no_categories(tmp_path):
    _setup_db(tmp_path, with_lab=True)
    navtree = import_module("bot.handlers.navigation_tree")
    from bot.navigation.tree import invalidate
    invalidate()
    ctx = SimpleNamespace(user_data={})
    _build_initial_stack(ctx)
    message = DummyMessage()

    query = SimpleNamespace(
        data="subject:1",
        message=message,
        answer=AsyncMock(),
        from_user=None,
        edit_message_text=message.edit_message_text,
    )
    update = SimpleNamespace(callback_query=query, effective_user=None)
    context = SimpleNamespace(user_data=ctx.user_data, bot=SimpleNamespace(copy_message=AsyncMock()))

    asyncio.run(navtree.navtree_callback(update, context))

    stack = NavStack(ctx.user_data)
    assert stack.peek() and stack.peek().kind == "subject"

    keyboard = message.sent[-1][1]
    buttons = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "nav:sec:1:theory" in buttons
    assert "nav:sec:1:lab" in buttons
    query2 = SimpleNamespace(
        data="nav:sec:1:theory",
        message=message,
        answer=AsyncMock(),
        from_user=None,
        edit_message_text=message.edit_message_text,
    )
    update2 = SimpleNamespace(callback_query=query2, effective_user=None)
    context2 = SimpleNamespace(user_data=ctx.user_data, bot=SimpleNamespace(copy_message=AsyncMock()))

    asyncio.run(navtree.navtree_callback(update2, context2))

    keyboard2 = message.sent[-1][1]
    buttons2 = [b.callback_data for row in keyboard2.inline_keyboard for b in row]
    for cat, _label in CATEGORIES:
        assert f"nav:section_option:1-theory-{cat}" not in buttons2
    assert "nav:section_option:1-theory-year" in buttons2
    assert "nav:section_option:1-theory-lecturer" in buttons2
