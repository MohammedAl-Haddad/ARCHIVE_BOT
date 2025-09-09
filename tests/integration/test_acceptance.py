import os
import asyncio
import itertools
from importlib import import_module
from types import SimpleNamespace
import re

import pytest

os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.handlers import ingestion
from bot.repo import rbac

pytestmark = pytest.mark.anyio


def setup_environment(monkeypatch):
    calls = []
    sent = []
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
        m = re.search(r"(//follow|//end|//cancel)$", text)
        intent = "none"
        if m:
            intent = m.group(1)[2:]
            text = text[: m.start()].strip()
        tag = text.split()[0].lstrip("#") if text.strip() else ""
        return (
            SimpleNamespace(
                year=None,
                content_type=tag,
                title="t",
                tags=[],
                lecture_no=None,
                lecturer=None,
                chain=SimpleNamespace(intent=intent),
            ),
            None,
        )

    async def fake_get_admin_with_permissions(user_id):
        return (1, ingestion.UPLOAD_CONTENT)

    async def fake_get_group_id_by_chat(chat_id):
        return (1, 1, 1)

    async def fake_get_binding(chat_id, thread_id):
        if thread_id == 1:
            return {"subject_id": 1, "subject_name": "s", "section": "theory"}
        return None

    async def fake_send_ephemeral(_ctx, _cid, text, **kwargs):
        sent.append(text)
        return None

    async def fake_copy_message(*args, **kwargs):
        return None

    async def fake_find_exact(*args, **kwargs):
        return None

    async def fake_insert_material(*args, **kwargs):
        return 1

    async def fake_attach_material(*args, **kwargs):
        return None

    async def fake_get_or_create_year(*args, **kwargs):
        return None

    async def fake_get_or_create_lecturer(*args, **kwargs):
        return None

    monkeypatch.setattr(ingestion, "insert_ingestion", fake_insert_ingestion)
    monkeypatch.setattr(ingestion, "parse_hashtags", fake_parse_hashtags)
    monkeypatch.setattr(ingestion, "get_admin_with_permissions", fake_get_admin_with_permissions)
    monkeypatch.setattr(ingestion, "get_group_id_by_chat", fake_get_group_id_by_chat)
    monkeypatch.setattr(ingestion, "get_binding", fake_get_binding)
    monkeypatch.setattr(ingestion, "send_ephemeral", fake_send_ephemeral)
    monkeypatch.setattr(ingestion, "attach_material", fake_attach_material)
    monkeypatch.setattr(ingestion, "find_exact", fake_find_exact)
    monkeypatch.setattr(ingestion, "insert_material", fake_insert_material)
    monkeypatch.setattr(ingestion, "get_or_create_year", fake_get_or_create_year)
    monkeypatch.setattr(ingestion, "get_or_create_lecturer", fake_get_or_create_lecturer)
    monkeypatch.setattr(ingestion, "get_file_unique_id_from_message", lambda *a, **k: None)

    bot = SimpleNamespace(copy_message=fake_copy_message)
    context = SimpleNamespace(user_data={}, chat_data={}, bot=bot)
    return context, calls, sent


def make_update(text, msg_id=1, thread_id=1):
    message = SimpleNamespace(
        caption=None,
        text=text,
        chat_id=111,
        message_id=msg_id,
        message_thread_id=thread_id,
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(id=111),
        effective_user=SimpleNamespace(id=42),
    )
    return update


async def test_topic_vs_general(monkeypatch):
    context, calls, sent = setup_environment(monkeypatch)

    await ingestion.ingestion_handler(make_update("#slides", thread_id=None), context)
    assert any("يُرجى" in m for m in sent)

    sent.clear()
    await ingestion.ingestion_handler(make_update("#slides", thread_id=1), context)
    assert any("✅" in m for m in sent)


async def test_follow_chain(monkeypatch):
    context, calls, sent = setup_environment(monkeypatch)
    msg_id = itertools.count(1)

    await ingestion.ingestion_handler(make_update("#slides //follow", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#board_images", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#audio //end", next(msg_id)), context)
    await ingestion.ingestion_handler(make_update("#video", next(msg_id)), context)

    assert calls == [
        (1, None, None),
        (2, 1, 1),
        (3, 1, 2),
        (4, None, None),
    ]


async def test_sensitivity_block(monkeypatch):
    context, calls, sent = setup_environment(monkeypatch)

    class DummyPolicy:
        def is_sensitive(self, text, filename=None, section=None):
            return "phi" in text

    monkeypatch.setattr(ingestion, "sensitivity_policy", DummyPolicy())

    await ingestion.ingestion_handler(make_update("#slides phi"), context)
    assert any("E-PHI-BLOCK" in m for m in sent)


def test_rbac_integration(repo_db):
    role = asyncio.run(rbac.create_role("mod", ["mods"]))
    asyncio.run(rbac.assign_role(1, role["id"]))
    asyncio.run(rbac.set_permission(role["id"], "delete"))
    assert asyncio.run(rbac.has_permission(1, "delete"))


async def test_navigation_visibility(monkeypatch):
    navtree = import_module("bot.handlers.navigation_tree")

    class DummyMessage:
        def __init__(self):
            self.sent = []

        async def reply_text(self, text, reply_markup=None):
            self.sent.append((text, reply_markup))

    update = SimpleNamespace(message=DummyMessage(), callback_query=None, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={}, application=SimpleNamespace(bot_data={}))

    async def empty_children(kind, ident, user_id):
        return []

    monkeypatch.setattr(navtree, "get_children", empty_children)
    await navtree.navtree_start(update, context)
    buttons = [b.callback_data for row in update.message.sent[-1][1].inline_keyboard for b in row]
    assert buttons == ["nav:back"]

    async def some_children(kind, ident, user_id):
        return [(1, "L1")]

    monkeypatch.setattr(navtree, "get_children", some_children)
    update2 = SimpleNamespace(message=DummyMessage(), callback_query=None, effective_user=SimpleNamespace(id=1))
    context2 = SimpleNamespace(user_data={}, application=SimpleNamespace(bot_data={}))
    await navtree.navtree_start(update2, context2)
    buttons2 = [b.callback_data for row in update2.message.sent[-1][1].inline_keyboard for b in row]
    assert "nav:level:1" in buttons2
