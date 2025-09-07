"""Repository helpers for linking Telegram entities to subjects and sections."""
from __future__ import annotations

import aiosqlite

from bot.db import base

async def upsert_group(tg_chat_id: int, title: str,
                       *, level_id: int | None = None,
                       term_id: int | None = None,
                       section_id: int | None = None) -> int:
    """Insert or update a group record and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO groups (tg_chat_id, title, level_id, term_id, section_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tg_chat_id) DO UPDATE SET
                    title=excluded.title,
                    level_id=excluded.level_id,
                    term_id=excluded.term_id,
                    section_id=excluded.section_id""",
            (tg_chat_id, title, level_id, term_id, section_id),
        )
        await db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        # On conflict SQLite returns 0; fetch existing id
        cur = await db.execute("SELECT id FROM groups WHERE tg_chat_id=?", (tg_chat_id,))
        row = await cur.fetchone()
        assert row is not None
        return row[0]


async def get_group(tg_chat_id: int) -> tuple | None:
    """Return group row for *tg_chat_id* or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, tg_chat_id, title, level_id, term_id, section_id FROM groups WHERE tg_chat_id=?",
            (tg_chat_id,),
        )
        return await cur.fetchone()


async def upsert_topic(group_id: int, tg_topic_id: int, subject_id: int,
                       *, section_id: int | None = None) -> int:
    """Insert or update a topic linking to a subject/section."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO topics (group_id, tg_topic_id, subject_id, section_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(group_id, tg_topic_id) DO UPDATE SET
                    subject_id=excluded.subject_id,
                    section_id=excluded.section_id""",
            (group_id, tg_topic_id, subject_id, section_id),
        )
        await db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        cur = await db.execute(
            "SELECT id FROM topics WHERE group_id=? AND tg_topic_id=?",
            (group_id, tg_topic_id),
        )
        row = await cur.fetchone()
        assert row is not None
        return row[0]


async def get_topic(group_id: int, tg_topic_id: int) -> tuple | None:
    """Return topic row for identifiers."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, group_id, tg_topic_id, subject_id, section_id FROM topics WHERE group_id=? AND tg_topic_id=?",
            (group_id, tg_topic_id),
        )
        return await cur.fetchone()
