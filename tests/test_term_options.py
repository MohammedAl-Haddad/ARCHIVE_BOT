import os
import asyncio
from importlib import import_module
from types import SimpleNamespace

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

import pytest


@pytest.fixture
def navtree():
    return import_module("bot.handlers.navigation_tree")


def test_term_without_resources(monkeypatch, navtree):
    async def _inner():
        from bot.navigation import tree as tree_module

        async def fake_list_term_resource_kinds(level_id: int, term_id: int):
            assert (level_id, term_id) == (1, 2)
            return []

        async def fake_can_view(user_id, kind, item_id):
            return True

        monkeypatch.setattr(tree_module, "list_term_resource_kinds", fake_list_term_resource_kinds)
        monkeypatch.setattr(tree_module, "can_view", fake_can_view)
        tree_module.invalidate()

        ctx = SimpleNamespace(user_data={})
        children = await navtree._load_children(ctx, "term", (1, 2), user_id=1)
        assert children == [("term_option", "subjects", "عرض المواد")]

    asyncio.run(_inner())


def test_term_with_resources(monkeypatch, navtree):
    async def _inner():
        from bot.navigation import tree as tree_module

        async def fake_list_term_resource_kinds(level_id: int, term_id: int):
            assert (level_id, term_id) == (1, 2)
            return ["attendance", "misc"]

        async def fake_can_view(user_id, kind, item_id):
            return True

        monkeypatch.setattr(tree_module, "list_term_resource_kinds", fake_list_term_resource_kinds)
        monkeypatch.setattr(tree_module, "can_view", fake_can_view)
        tree_module.invalidate()

        ctx = SimpleNamespace(user_data={})
        children = await navtree._load_children(ctx, "term", (1, 2), user_id=1)
        assert ("term_option", "subjects", "عرض المواد") in children
        assert ("term_option", "attendance", "جدول الحضور 🗓️") in children
        assert ("term_option", "misc", "محتوى متنوع 📦") in children

    asyncio.run(_inner())
