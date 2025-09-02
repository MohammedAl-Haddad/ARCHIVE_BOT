import asyncio
import os
import aiosqlite
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.db import base as db_base
from bot.db import subjects, materials
from bot.navigation import NavStack


class DummyMessage:
    def __init__(self):
        self.sent = []
        self.chat_id = 100
        self.message_thread_id = 200

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))

    async def edit_message_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


def test_syllabus_section_sends_material(tmp_path):
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

        await materials.insert_material(
            1, "theory", "lecture", "t", tg_storage_chat_id=1, tg_storage_msg_id=11
        )
        await materials.insert_material(
            1, "lab", "lecture", "l", tg_storage_chat_id=1, tg_storage_msg_id=12
        )
        await materials.insert_material(
            1, "theory", "syllabus", "sy", tg_storage_chat_id=9, tg_storage_msg_id=99
        )

        navtree = import_module("bot.handlers.navigation_tree")

        ctx = SimpleNamespace(user_data={})
        children = await navtree._load_children(ctx, "subject", 1, user_id=None)
        assert ("section", "1-syllabus", "التوصيف 📄") in children

        stack = NavStack(ctx.user_data)
        stack.push(("subject", 1, "Sub1"))

        copy_calls = []

        async def fake_copy_message(chat_id, from_chat_id, message_id, message_thread_id=None):
            copy_calls.append((chat_id, from_chat_id, message_id, message_thread_id))

        message = DummyMessage()
        query = SimpleNamespace(
            data="section:1-syllabus",
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

        assert copy_calls == [(
            message.chat_id,
            9,
            99,
            message.message_thread_id,
        )]

    asyncio.run(_inner())

