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
from bot.db import subjects, materials
from bot.navigation.nav_stack import NavStack, Node


CATEGORIES = [
    ("syllabus", "التوصيف 📄", 9, 99),
    ("glossary", "المفردات الدراسية 📖", 10, 100),
    ("practical", "الواقع التطبيقي ⚙️", 11, 101),
    ("references", "مراجع 📚", 12, 102),
    ("skills", "مهارات 🧠", 13, 103),
    ("open_source_projects", "مشاريع مفتوحة المصدر 🛠️", 14, 104),
]


class DummyMessage:
    def __init__(self):
        self.sent = []
        self.chat_id = 100
        self.message_thread_id = 200

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))

    async def edit_message_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


def test_section_category_buttons_send_material(tmp_path):
    async def _inner():
        db_path = tmp_path / "test.db"
        db_base.DB_PATH = subjects.DB_PATH = materials.DB_PATH = str(db_path)
        await db_base.init_db()

        async with aiosqlite.connect(db_base.DB_PATH) as db:
            await db.execute("INSERT INTO levels (name) VALUES ('L1')")
            await db.execute("INSERT INTO terms (name) VALUES ('T1')")
            await db.execute(
                "INSERT INTO subjects (code, name, level_id, term_id) VALUES ('S1','Sub1',1,1)"
            )
            await db.commit()

        # Ensure section exists
        await materials.insert_material(
            1, "theory", "lecture", "t", tg_storage_chat_id=1, tg_storage_msg_id=11
        )

        for cat, _label, chat_id, msg_id in CATEGORIES:
            await materials.insert_material(
                1,
                "theory",
                cat,
                f"{cat} title",
                tg_storage_chat_id=chat_id,
                tg_storage_msg_id=msg_id,
            )

        navtree = import_module("bot.handlers.navigation_tree")

        ctx = SimpleNamespace(user_data={})
        children = await navtree._load_children(ctx, "section", (1, "theory"), user_id=None)

        category_ids = {cat for cat, _label, _chat_id, _msg_id in CATEGORIES}
        category_children = [
            c for c in children if c[1].split("-")[-1] in category_ids
        ]
        assert len(category_children) == len(CATEGORIES)
        for cat, label, _, _ in CATEGORIES:
            assert ("section_option", f"1-theory-{cat}", label) in children

        stack = NavStack(ctx.user_data)
        stack.push(Node("subject", 1, "Sub1"))
        stack.push(Node("section", (1, "theory"), "نظري 📘"))

        copy_calls = []

        async def fake_copy_message(chat_id, from_chat_id, message_id, message_thread_id=None):
            copy_calls.append((chat_id, from_chat_id, message_id, message_thread_id))

        message = DummyMessage()

        for cat, _label, chat_id, msg_id in CATEGORIES:
            query = SimpleNamespace(
                data=f"section_option:1-theory-{cat}",
                message=message,
                answer=AsyncMock(),
                from_user=SimpleNamespace(id=1),
            )
            update = SimpleNamespace(
                callback_query=query,
                effective_user=SimpleNamespace(id=1),
            )
            context = SimpleNamespace(
                user_data=ctx.user_data,
                bot=SimpleNamespace(copy_message=fake_copy_message),
            )

            await navtree.navtree_callback(update, context)
            assert copy_calls[-1] == (
                message.chat_id,
                chat_id,
                msg_id,
                message.message_thread_id,
            )

        assert len(copy_calls) == len(CATEGORIES)

    asyncio.run(_inner())

