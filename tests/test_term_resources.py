import asyncio
import os
import aiosqlite

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.db import base as db_base
from bot.db import term_resources


def test_term_resource_kinds(tmp_path):
    async def _inner():
        db_path = tmp_path / "test.db"
        db_base.DB_PATH = term_resources.DB_PATH = str(db_path)
        await db_base.init_db()
        async with aiosqlite.connect(db_base.DB_PATH) as db:
            await db.execute("INSERT INTO terms (name) VALUES ('T1')")
            await db.commit()

        for i, kind in enumerate(term_resources.TermResourceKind):
            await term_resources.insert_term_resource(1, kind, 100 + i, 200 + i)
            assert await term_resources.has_term_resource(1, kind)
            chat_id, msg_id = await term_resources.get_latest_term_resource(1, kind)
            assert (chat_id, msg_id) == (100 + i, 200 + i)

        kinds = await term_resources.list_term_resource_kinds(1)
        assert set(kinds) == {k.value for k in term_resources.TermResourceKind}

    asyncio.run(_inner())
