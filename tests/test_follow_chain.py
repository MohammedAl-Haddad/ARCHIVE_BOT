import os
import pytest
from types import SimpleNamespace
import itertools
import time

os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers import ingestion

pytestmark = pytest.mark.anyio


def setup_environment(monkeypatch):
    calls = []
    counter = itertools.count(1)

    async def fake_insert_ingestion(
        tg_message_id,
        admin_id,
        status="pending",
        action="add",
        file_unique_id=None,
        chain_id=None,
        parent_ingestion_id=None,
    ):
        iid = next(counter)
        calls.append((iid, chain_id, parent_ingestion_id))
        return iid

    async def fake_parse_hashtags(text):
        tag = text.lstrip("#")
        return (
            SimpleNamespace(
                year=None,
                content_type=tag,
                title="t",
                lecturer=None,
                tags=[],
                lecture_no=None,
            ),
            None,
        )

    async def fake_get_admin_with_permissions(user_id):
        return (1, ingestion.UPLOAD_CONTENT)

    async def fake_get_group_id_by_chat(chat_id):
        return (1, 1, 1)

    async def fake_get_binding(chat_id, thread_id):
        return {"subject_id": 1, "subject_name": "s", "section": "theory"}

    async def fake_send_ephemeral(*args, **kwargs):
        return None

    async def fake_copy_message(*args, **kwargs):
        return None

    def fake_get_file_unique_id_from_message(message):
        return None

    async def fake_attach_material(*args, **kwargs):
        return None

    monkeypatch.setattr(ingestion, "insert_ingestion", fake_insert_ingestion)
    monkeypatch.setattr(ingestion, "parse_hashtags", fake_parse_hashtags)
    monkeypatch.setattr(ingestion, "get_admin_with_permissions", fake_get_admin_with_permissions)
    monkeypatch.setattr(ingestion, "get_group_id_by_chat", fake_get_group_id_by_chat)
    monkeypatch.setattr(ingestion, "get_binding", fake_get_binding)
    monkeypatch.setattr(ingestion, "send_ephemeral", fake_send_ephemeral)
    monkeypatch.setattr(ingestion, "attach_material", fake_attach_material)
    async def fake_find_exact(*args, **kwargs):
        return None

    async def fake_insert_material(*args, **kwargs):
        return 1

    monkeypatch.setattr(ingestion, "find_exact", fake_find_exact)
    monkeypatch.setattr(ingestion, "insert_material", fake_insert_material)
    monkeypatch.setattr(ingestion, "get_or_create_year", lambda *a, **k: None)
    monkeypatch.setattr(ingestion, "get_or_create_lecturer", lambda *a, **k: None)
    monkeypatch.setattr(ingestion, "get_file_unique_id_from_message", fake_get_file_unique_id_from_message)

    bot = SimpleNamespace(copy_message=fake_copy_message)
    context = SimpleNamespace(user_data={}, chat_data={}, bot=bot)

    return context, calls


def make_update(text, msg_id=1):
    message = SimpleNamespace(
        caption=None,
        text=text,
        chat_id=111,
        message_id=msg_id,
        message_thread_id=1,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )
    return update


async def test_follow_chain_sequence(monkeypatch):
    context, calls = setup_environment(monkeypatch)
    msg_id = itertools.count(1)

    await ingestion.ingestion_handler(make_update("#slides", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("//follow", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#board_images", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#audio", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("//end", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#video", next(msg_id)), context)

    assert calls == [
        (1, None, None),
        (2, 1, 1),
        (3, 1, 2),
        (4, None, None),
    ]


async def test_cancel_follow_chain(monkeypatch):
    context, calls = setup_environment(monkeypatch)
    msg_id = itertools.count(1)

    await ingestion.ingestion_handler(make_update("#slides", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("//follow", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#board_images", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("//cancel", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#video", next(msg_id)), context)

    assert calls == [
        (1, None, None),
        (2, 1, 1),
        (3, None, None),
    ]


async def test_chain_timeout(monkeypatch):
    context, calls = setup_environment(monkeypatch)
    msg_id = itertools.count(1)

    await ingestion.ingestion_handler(make_update("#slides", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("//follow", next(msg_id)), context)
    # expire chain
    key = (111, 42)
    context.chat_data["follow_chains"][key]["expires_at"] = time.time() - 1
    await ingestion.ingestion_handler(make_update("#board_images", next(msg_id)), context)

    assert calls == [
        (1, None, None),
        (2, None, None),
    ]
