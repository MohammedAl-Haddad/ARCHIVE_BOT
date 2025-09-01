import os
import pytest
from types import SimpleNamespace

os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers import ingestion
from tests.helpers import TERM_RESOURCE_TAGS

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("kind, tags", TERM_RESOURCE_TAGS.items())
async def test_term_resource_ingestion(kind, tags, monkeypatch):
    calls = []

    async def fake_insert_term_resource(term_id, k, chat_id, msg_id):
        calls.append((term_id, k, chat_id, msg_id))

    async def fake_get_admin_with_permissions(user_id):
        return (1, ingestion.UPLOAD_CONTENT)

    async def fake_get_group_id_by_chat(chat_id):
        return (None, None, 1)

    async def fake_send_ephemeral(*args, **kwargs):
        return None

    def fake_get_file_unique_id_from_message(message):
        return None

    monkeypatch.setattr(ingestion, "insert_term_resource", fake_insert_term_resource)
    monkeypatch.setattr(ingestion, "get_admin_with_permissions", fake_get_admin_with_permissions)
    monkeypatch.setattr(ingestion, "get_group_id_by_chat", fake_get_group_id_by_chat)
    monkeypatch.setattr(ingestion, "send_ephemeral", fake_send_ephemeral)
    monkeypatch.setattr(ingestion, "get_file_unique_id_from_message", fake_get_file_unique_id_from_message)

    for tag in tags:
        calls.clear()
        message = SimpleNamespace(
            caption=None,
            text=tag,
            chat_id=111,
            message_id=222,
            message_thread_id=None,
        )
        update = SimpleNamespace(
            effective_message=message,
            effective_chat=SimpleNamespace(id=111),
            effective_user=SimpleNamespace(id=42),
        )
        context = SimpleNamespace(user_data={})

        await ingestion.ingestion_handler(update, context)

        assert calls == [(1, kind, 111, 222)]
