import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers import ingestion

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _prepare(monkeypatch, binding):
    insert_calls = []
    attach_calls = []
    sent_msgs = []

    async def fake_insert_material(subject_id, section, category, title, **kwargs):
        insert_calls.append((subject_id, section, category, title))
        return 10

    async def fake_insert_ingestion(msg_id, admin_id, action="add", file_unique_id=None):
        return 99

    async def fake_attach_material(ingestion_id, material_id, status):
        attach_calls.append((ingestion_id, material_id, status))

    async def fake_get_admin_with_permissions(user_id):
        return (1, ingestion.UPLOAD_CONTENT)

    async def fake_get_group_id_by_chat(chat_id):
        return (1, 1, 1)

    async def fake_get_binding(chat_id, thread_id):
        return binding[thread_id] if thread_id in binding else None

    async def fake_find_exact(*args, **kwargs):
        return None

    async def fake_send_ephemeral(*args, **kwargs):
        sent_msgs.append(kwargs.get("text") or args[2])
        return None

    def fake_get_file_unique_id_from_message(message):
        return None

    async def fake_copy_message(*args, **kwargs):
        return None

    monkeypatch.setattr(ingestion, "insert_material", fake_insert_material)
    monkeypatch.setattr(ingestion, "insert_ingestion", fake_insert_ingestion)
    monkeypatch.setattr(ingestion, "attach_material", fake_attach_material)
    monkeypatch.setattr(ingestion, "get_admin_with_permissions", fake_get_admin_with_permissions)
    monkeypatch.setattr(ingestion, "get_group_id_by_chat", fake_get_group_id_by_chat)
    monkeypatch.setattr(ingestion, "get_binding", fake_get_binding)
    monkeypatch.setattr(ingestion, "find_exact", fake_find_exact)
    monkeypatch.setattr(ingestion, "send_ephemeral", fake_send_ephemeral)
    monkeypatch.setattr(ingestion, "get_file_unique_id_from_message", fake_get_file_unique_id_from_message)

    context = SimpleNamespace(user_data={}, bot=SimpleNamespace(copy_message=fake_copy_message))

    return insert_calls, attach_calls, sent_msgs, context


async def test_single_card_in_topic(monkeypatch):
    binding = {333: {"subject_id": 1, "section": "theory", "subject_name": "sub"}}
    insert_calls, attach_calls, _, context = await _prepare(monkeypatch, binding)

    message = SimpleNamespace(
        caption=None,
        text="#التوصيف",
        chat_id=111,
        message_id=222,
        message_thread_id=333,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )

    await ingestion.ingestion_handler(update, context)

    assert insert_calls[0][:3] == (1, "theory", "syllabus")
    assert attach_calls == [(99, 10, "pending")]


async def test_single_card_general_chat_without_binding(monkeypatch):
    binding = {}
    insert_calls, attach_calls, sent_msgs, context = await _prepare(monkeypatch, binding)

    message = SimpleNamespace(
        caption=None,
        text="#التوصيف",
        chat_id=111,
        message_id=222,
        message_thread_id=None,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )

    await ingestion.ingestion_handler(update, context)

    assert insert_calls == []
    assert attach_calls == []
    assert sent_msgs and "يُرجى النشر داخل موضوع المادة الصحيح" in sent_msgs[0]


async def test_single_card_general_chat_with_binding(monkeypatch):
    binding = {0: {"subject_id": 1, "section": None, "subject_name": "sub"}}
    insert_calls, attach_calls, _, context = await _prepare(monkeypatch, binding)

    message = SimpleNamespace(
        caption=None,
        text="#التوصيف",
        chat_id=111,
        message_id=222,
        message_thread_id=None,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )

    await ingestion.ingestion_handler(update, context)

    assert insert_calls[0][:3] == (1, "theory", "syllabus")
    assert attach_calls == [(99, 10, "pending")]

