import asyncio
from importlib import import_module


class DummyContext:
    def __init__(self):
        self.user_data = {}

def test_load_children_cache(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("ARCHIVE_CHANNEL_ID", "1")
    monkeypatch.setenv("OWNER_TG_ID", "1")
    navigation_tree = import_module("bot.handlers.navigation_tree")

    calls = {"count": 0}

    async def fake_get_children(kind, ident, user_id):
        calls["count"] += 1
        return [(1, "Item 1"), (2, "Item 2")]

    monkeypatch.setattr(navigation_tree, "get_children", fake_get_children)

    async def run():
        ctx = DummyContext()
        children1 = await navigation_tree._load_children(ctx, "root", None, None)
        assert calls["count"] == 1
        children2 = await navigation_tree._load_children(ctx, "root", None, None)
        assert calls["count"] == 1
        assert children1 == children2
        ctx.user_data[navigation_tree.LAST_CHILDREN_KEY]["timestamp"] -= (
            navigation_tree.LAST_CHILDREN_TTL_SECONDS + 1
        )
        await navigation_tree._load_children(ctx, "root", None, None)
        assert calls["count"] == 2

    asyncio.run(run())
