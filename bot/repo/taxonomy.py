"""Repository helpers for dynamic taxonomy tables.

The original implementation used textual ``key`` identifiers for
sections, cards and item types.  The database schema no longer includes
those columns; instead, callers refer to records via their numeric
primary keys.  The functions here expose a very small CRUD interface
returning tuples that also include ``created_at`` and ``updated_at``
timestamps for convenience.
"""
from __future__ import annotations

import aiosqlite

from bot.db import base

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
async def create_section(
    label_ar: str,
    label_en: str,
    *,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> int:
    """Insert a section and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO sections (label_ar, label_en, is_enabled, sort_order)
                VALUES (?, ?, ?, ?)""",
            (label_ar, label_en, int(is_enabled), sort_order),
        )
        await db.commit()
        return cur.lastrowid


async def get_section(section_id: int) -> tuple | None:
    """Return section row for *section_id* or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, label_ar, label_en, is_enabled, sort_order, created_at, updated_at FROM sections WHERE id=?",
            (section_id,),
        )
        return await cur.fetchone()


async def update_section(section_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [section_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE sections SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_section(section_id: int) -> None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM sections WHERE id=?", (section_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Cards (material categories)
# ---------------------------------------------------------------------------
async def create_card(
    label_ar: str,
    label_en: str,
    *,
    section_id: int | None = None,
    show_when_empty: bool = False,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> int:
    """Insert a card and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO cards
                (section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (
                section_id,
                label_ar,
                label_en,
                int(show_when_empty),
                int(is_enabled),
                sort_order,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_card(card_id: int) -> tuple | None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order, created_at, updated_at FROM cards WHERE id=?",
            (card_id,),
        )
        return await cur.fetchone()


async def update_card(card_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [card_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE cards SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_card(card_id: int) -> None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM cards WHERE id=?", (card_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Item types
# ---------------------------------------------------------------------------
async def create_item_type(
    label_ar: str,
    label_en: str,
    *,
    requires_lecture: bool = False,
    allows_year: bool = True,
    allows_lecturer: bool = True,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> int:
    """Insert an item type and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO item_types
                (label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                label_ar,
                label_en,
                int(requires_lecture),
                int(allows_year),
                int(allows_lecturer),
                int(is_enabled),
                sort_order,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_item_type(item_type_id: int) -> tuple | None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order, created_at, updated_at FROM item_types WHERE id=?",
            (item_type_id,),
        )
        return await cur.fetchone()


async def update_item_type(item_type_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [item_type_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE item_types SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_item_type(item_type_id: int) -> None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM item_types WHERE id=?", (item_type_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Subject section enablement
# ---------------------------------------------------------------------------
async def set_subject_section_enable(
    subject_id: int,
    section_id: int,
    *,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> None:
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            """INSERT INTO subject_section_enable
                (subject_id, section_id, is_enabled, sort_order)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subject_id, section_id)
                DO UPDATE SET is_enabled=excluded.is_enabled, sort_order=excluded.sort_order""",
            (subject_id, section_id, int(is_enabled), sort_order),
        )
        await db.commit()


async def get_enabled_sections_for_subject(subject_id: int) -> list[tuple]:
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT section_id, is_enabled, sort_order FROM subject_section_enable WHERE subject_id=? ORDER BY sort_order",
            (subject_id,),
        )
        return await cur.fetchall()


__all__ = [
    "create_section",
    "get_section",
    "update_section",
    "delete_section",
    "create_card",
    "get_card",
    "update_card",
    "delete_card",
    "create_item_type",
    "get_item_type",
    "update_item_type",
    "delete_item_type",
    "set_subject_section_enable",
    "get_enabled_sections_for_subject",
]
