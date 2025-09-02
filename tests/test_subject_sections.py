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

        new_categories = [
            "vocabulary",
            "applications",
            "references",
            "skills",
            "open_source_projects",
            "glossary",
            "practical",
        ]
        for cat in new_categories:
            await materials.insert_material(
                1, "theory", cat, f"{cat} title", url="http://ex.com"
            )
        # Insert a syllabus record with category='syllabus'
        await materials.insert_material(
            1, "theory", "syllabus", "syllabus title", url="http://ex.com"
        )
        sections = await subjects.get_available_sections_for_subject(1)
        assert "theory" in sections
        assert "syllabus" in sections

        for cat in [
            "references",
            "skills",
            "open_source_projects",
            "glossary",
            "practical",
        ]:
            assert cat in sections

        for cat in ["vocabulary", "applications"]:
            assert cat not in sections

    asyncio.run(_inner())
