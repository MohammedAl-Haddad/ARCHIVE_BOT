import os
import asyncio
import logging
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.navigation import NavStack


class DummyMessage:
    def __init__(self):
        self.sent = []

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))

    async def edit_message_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


@pytest.fixture
def navtree():
    return import_module("bot.handlers.navigation_tree")


def test_nav_stack_path():
    ud_new = {}
    stack = NavStack(ud_new)
    stack.push(("level", 1, "L1"))
    stack.push(("term", 1, "T1"))
    stack.push(("subject", 1, "S1"))
    stack.push(("year", 1, "Y1"))
    stack.push(("section", "sec", "Sec"))
    stack.push(("lecture", None, "Mat"))
    new_path = stack.path_text()

    assert new_path == "L1 / T1 / S1 / Y1 / Sec / Mat"


@pytest.fixture
def large_dataset(monkeypatch, navtree):
    async def fake_get_children(kind, ident, user_id):
        await asyncio.sleep(0.01)
        return [(i, f"Item {i}") for i in range(1000)]

    monkeypatch.setattr(navtree, "get_children", fake_get_children)
    return navtree


def test_db_time_logged(large_dataset, caplog):
    navtree = large_dataset
    update = SimpleNamespace(message=DummyMessage(), callback_query=None, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    async def run():
        with caplog.at_level(logging.INFO):
            await navtree._render(update, context, "root", None, 1, action="test")

    asyncio.run(run())

    record = next(r for r in caplog.records if "db_time=" in r.message)
    db_time_ms = float(record.message.split("db_time=")[1].split("ms")[0])
    assert db_time_ms > 0


def test_back_button_pops_stack(monkeypatch, navtree):
    context = SimpleNamespace(user_data={})
    stack = NavStack(context.user_data)
    stack.push(("level", 1, "L1"))
    stack.push(("term", 2, "T1"))

    query = SimpleNamespace(data="nav:back", message=DummyMessage(), answer=AsyncMock())
    update = SimpleNamespace(callback_query=query, effective_user=None)

    render_mock = AsyncMock()
    monkeypatch.setattr(navtree, "_render_current", render_mock)

    asyncio.run(navtree.navtree_callback(update, context))

    assert stack.path_text() == "L1"
    render_mock.assert_called_once()


def test_root_renders_back_button(monkeypatch, navtree):
    async def fake_get_children(kind, ident, user_id):
        return []

    monkeypatch.setattr(navtree, "get_children", fake_get_children)

    update = SimpleNamespace(
        message=DummyMessage(),
        callback_query=None,
        effective_user=SimpleNamespace(id=1),
    )
    context = SimpleNamespace(user_data={})

    asyncio.run(navtree._render(update, context, "root", None, 1, action="test"))

    _, keyboard = update.message.sent[-1]
    assert any(
        button.callback_data == "nav:back"
        for row in keyboard.inline_keyboard
        for button in row
    )


def test_back_button_at_root_returns_main_menu(navtree):
    class DummyQuery:
        def __init__(self):
            self.data = "nav:back"
            self.message = DummyMessage()
            self.from_user = None
            self.answered = False

        async def edit_message_text(self, text, reply_markup=None):
            await self.message.edit_message_text(text, reply_markup)

        async def answer(self):
            self.answered = True

    query = DummyQuery()
    update = SimpleNamespace(callback_query=query, effective_user=None)
    context = SimpleNamespace(user_data={})

    asyncio.run(navtree.navtree_callback(update, context))

    assert query.answered
    text, reply_markup = query.message.sent[-1]
    assert text == "اختر من القائمة:"
    assert reply_markup.inline_keyboard[0][0].callback_data.startswith("menu:")
    assert NavStack(context.user_data).peek() is None


def test_permission_filter(monkeypatch, navtree):
    from bot.navigation import tree as tree_module

    async def fake_loader():
        return [(1, "L1"), (2, "L2")]

    async def fake_can_view(user_id, kind, item_id):
        return item_id == 1

    tree_module.invalidate()
    monkeypatch.setitem(tree_module.KIND_TO_LOADER, "root", fake_loader)
    monkeypatch.setattr(tree_module, "can_view", fake_can_view)

    ctx = SimpleNamespace(user_data={})

    async def run():
        return await navtree._load_children(ctx, "root", None, user_id=5)

    children = asyncio.run(run())
    assert children == [("level", 1, "L1")]


def test_parse_id_handles_composite(navtree):
    assert navtree._parse_id("5") == 5
    assert navtree._parse_id("abc") == "abc"
    assert navtree._parse_id("1-2") == (1, 2)
    assert navtree._parse_id("123-theory") == (123, "theory")


def test_load_children_merges_level_and_term(monkeypatch, navtree):
    async def fake_get_children(kind, ident, user_id):
        assert kind == "level"
        assert ident == 1
        return [(1, "T1"), (2, "T2")]

    monkeypatch.setattr(navtree, "get_children", fake_get_children)

    ctx = SimpleNamespace(user_data={})

    async def run():
        return await navtree._load_children(ctx, "level", 1, user_id=None)

    children = asyncio.run(run())
    assert children == [("term", "1-1", "T1"), ("term", "1-2", "T2")]


def test_load_children_merges_subject_and_section(monkeypatch, navtree):
    async def fake_get_children(kind, ident, user_id):
        assert kind == "subject"
        assert ident == 7
        return ["theory", "lab"]

    monkeypatch.setattr(navtree, "get_children", fake_get_children)

    ctx = SimpleNamespace(user_data={})

    async def run():
        return await navtree._load_children(ctx, "subject", 7, user_id=None)

    children = asyncio.run(run())
    assert children == [
        ("section", "7-theory", "theory"),
        ("section", "7-lab", "lab"),
    ]


def test_get_children_accepts_composite(monkeypatch):
    from bot.navigation import tree as tree_module

    called = {}

    async def fake_loader(level_id, term_id):
        called["args"] = (level_id, term_id)
        return []

    monkeypatch.setitem(tree_module.KIND_TO_LOADER, "term", fake_loader)

    asyncio.run(tree_module.get_children("term", (3, 4)))

    assert called["args"] == (3, 4)
