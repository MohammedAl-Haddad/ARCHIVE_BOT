import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# Ensure required environment variables for importing bot modules
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers.ingestion import handle_duplicate_decision


class DummyMessage:
    def __init__(self):
        self.chat_id = 123
        self.message_thread_id = None
        self.deleted = False

    async def delete(self):
        self.deleted = True


class DummyQuery:
    def __init__(self, user_id):
        self.from_user = SimpleNamespace(id=user_id)
        self.data = "dup:cancel:1:0"
        self.message = DummyMessage()

    async def answer(self):
        pass

    async def edit_message_text(self, text):
        self.edited_text = text

    async def edit_message_reply_markup(self, markup):
        self.edited_markup = markup


def _make_context():
    ctx = {"replace_ctx": {1: {"tg_user_id": 42, "admin_id": 5}}}
    bot = SimpleNamespace(send_message=AsyncMock())
    return SimpleNamespace(user_data=ctx, bot=bot)


def _run(user_id, owner_flag):
    query = DummyQuery(user_id)
    context = _make_context()
    update = SimpleNamespace(callback_query=query)

    async def runner():
        with patch("bot.handlers.ingestion.send_ephemeral", AsyncMock()), patch(
            "bot.handlers.ingestion.is_owner", return_value=owner_flag
        ):
            await handle_duplicate_decision(update, context)
        return query.message.deleted

    return asyncio.run(runner())


def test_sender_can_cancel_duplicate():
    assert _run(42, False)


def test_owner_can_cancel_duplicate():
    assert _run(1, True)
