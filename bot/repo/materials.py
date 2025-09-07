"""Repository helpers for material records.

These functions expose a minimal CRUD interface for the ``materials``
table using the new dynamic-taxonomy columns ``section_id``,
``category_id`` and ``item_type_id``.  Only a small subset of the
production queries is implemented which is sufficient for unit tests
and for handlers that merely need basic persistence.
"""
from __future__ import annotations

import aiosqlite

from bot.db import base

async def insert_material(
    subject_id: int,
    section_id: int | None,
    category_id: int | None,
    item_type_id: int | None,
    title: str,
    *,
    url: str | None = None,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    lecture_no: int | None = None,
    content_hash: str | None = None,
    tg_storage_chat_id: int | None = None,
    tg_storage_msg_id: int | None = None,
    file_unique_id: str | None = None,
    source_chat_id: int | None = None,
    source_topic_id: int | None = None,
    source_message_id: int | None = None,
    created_by_admin_id: int | None = None,
) -> int:
    """Insert a material record and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO materials (
                    subject_id, section_id, category_id, item_type_id, title, url,
                    year_id, lecturer_id, lecture_no, content_hash,
                    tg_storage_chat_id, tg_storage_msg_id, file_unique_id,
                    source_chat_id, source_topic_id, source_message_id,
                    created_by_admin_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                subject_id,
                section_id,
                category_id,
                item_type_id,
                title,
                url,
                year_id,
                lecturer_id,
                lecture_no,
                content_hash,
                tg_storage_chat_id,
                tg_storage_msg_id,
                file_unique_id,
                source_chat_id,
                source_topic_id,
                source_message_id,
                created_by_admin_id,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_material(material_id: int) -> tuple | None:
    """Return material row for *material_id* or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT * FROM materials WHERE id=?",
            (material_id,),
        )
        return await cur.fetchone()


async def update_material_storage(
    material_id: int,
    chat_id: int,
    msg_id: int,
    *,
    file_unique_id: str | None = None,
) -> None:
    """Update storage chat/message identifiers for a material."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "UPDATE materials SET tg_storage_chat_id=?, tg_storage_msg_id=?, file_unique_id=? WHERE id=?",
            (chat_id, msg_id, file_unique_id, material_id),
        )
        await db.commit()


async def delete_material(material_id: int) -> None:
    """Remove a material record."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()


async def find_by_hash(content_hash: str) -> tuple | None:
    """Return the first material row matching *content_hash*."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT * FROM materials WHERE content_hash=?",
            (content_hash,),
        )
        return await cur.fetchone()
