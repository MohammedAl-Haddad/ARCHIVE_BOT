import asyncio
import os
import aiosqlite

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.db import base as db_base
from bot.db import subjects, materials


def test_new_sections_returned(tmp_path):
    async def _inner():
        db_path = tmp_path / "test.db"
        db_base.DB_PATH = subjects.DB_PATH = materials.DB_PATH = str(db_path)
        await db_base.init_db()
        async with aiosqlite.connect(db_base.DB_PATH) as db:
            await db.execute("INSERT INTO levels (name) VALUES ('L1')")
            await db.execute("INSERT INTO terms (name) VALUES ('T1')")
            await db.execute(
                "INSERT INTO subjects (code, name, level_id, term_id) VALUES ('S1','Sub1',1,1)"
            )
            await db.commit()
        new_sections = ["vocabulary", "references", "skills", "open_source_projects"]
        for sec in new_sections:
            await materials.insert_material(1, sec, "lecture", f"{sec} title", url="http://ex.com")
        # Insert a syllabus record and ensure it is returned
        await materials.insert_material(1, "syllabus", "syllabus", "syllabus title", url="http://ex.com")
        sections = await subjects.get_available_sections_for_subject(1)
        assert set(new_sections).issubset(set(sections))
        assert "syllabus" in sections
    asyncio.run(_inner())
