import os
import pytest
from types import SimpleNamespace

os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers import ingestion

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("tag, expected_category", [
    ("#نموذج_النصفي\n#1446", "exam_mid"),
    ("#نموذج_النهائي\n#1446", "exam_final"),
])
async def test_exam_ingestion(tag, expected_category, monkeypatch):
    insert_calls = []
    attach_calls = []

    async def fake_insert_material(subject_id, section, category, title, **kwargs):
        insert_calls.append((subject_id, section, category, title, kwargs))
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
        return {"subject_id": 1, "section": "theory", "subject_name": "sub"}

    async def fake_get_or_create_year(year):
        return 1

    async def fake_find_exact(*args, **kwargs):
        return None

    async def fake_send_ephemeral(*args, **kwargs):
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
    monkeypatch.setattr(ingestion, "get_or_create_year", fake_get_or_create_year)
    monkeypatch.setattr(ingestion, "find_exact", fake_find_exact)
    monkeypatch.setattr(ingestion, "send_ephemeral", fake_send_ephemeral)
    monkeypatch.setattr(ingestion, "get_file_unique_id_from_message", fake_get_file_unique_id_from_message)

    message = SimpleNamespace(
        caption=None,
        text=tag,
        chat_id=111,
        message_id=222,
        message_thread_id=333,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )
    context = SimpleNamespace(user_data={}, bot=SimpleNamespace(copy_message=fake_copy_message))

    await ingestion.ingestion_handler(update, context)

    assert insert_calls[0][2] == expected_category
    assert attach_calls == [(99, 10, "pending")]
