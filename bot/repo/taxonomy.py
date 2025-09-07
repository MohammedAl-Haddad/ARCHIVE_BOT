"""Helpers for managing the dynamic taxonomy tables.

The repository exposes CRUD operations for the following tables:

* ``sections``
* ``cards`` (material categories)
* ``item_types``
* ``subject_section_enable``

Each function returns basic Python types (``int`` ids or ``tuple`` rows)
so that higher level code can remain agnostic of the underlying SQL
implementation.  All operations are asynchronous and use the global
``DB_PATH`` from :mod:`bot.db.base`.
"""
from __future__ import annotations

import aiosqlite

from bot.db import base

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
async def create_section(key: str, label_ar: str, label_en: str,
                        *, is_enabled: bool = True, sort_order: int = 0) -> int:
    """Insert a new section and return its database id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO sections (key, label_ar, label_en, is_enabled, sort_order)
                VALUES (?, ?, ?, ?, ?)""",
            (key, label_ar, label_en, int(is_enabled), sort_order),
        )
        await db.commit()
        return cur.lastrowid


async def get_section(key: str) -> tuple | None:
    """Return the section row for *key* or ``None`` if not found."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, key, label_ar, label_en, is_enabled, sort_order FROM sections WHERE key=?",
            (key,),
        )
        return await cur.fetchone()


async def update_section(section_id: int, **fields) -> None:
    """Update a section row using keyword *fields*.

    Only supplied fields are updated.  Allowed keys: ``key``, ``label_ar``,
    ``label_en``, ``is_enabled`` and ``sort_order``.
    """
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [section_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE sections SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_section(section_id: int) -> None:
    """Delete section with *section_id*."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM sections WHERE id=?", (section_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Cards (material categories)
# ---------------------------------------------------------------------------
async def create_card(key: str, label_ar: str, label_en: str, *,
                      section_id: int | None = None,
                      show_when_empty: bool = False,
                      is_enabled: bool = True,
                      sort_order: int = 0) -> int:
    """Insert a card (material category) and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO cards
                (key, label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                key,
                label_ar,
                label_en,
                section_id,
                int(show_when_empty),
                int(is_enabled),
                sort_order,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_card(key: str) -> tuple | None:
    """Return card row for *key* or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, key, label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order FROM cards WHERE key=?",
            (key,),
        )
        return await cur.fetchone()


async def update_card(card_id: int, **fields) -> None:
    """Update card row with given *fields*.

    Allowed keys: ``key``, ``label_ar``, ``label_en``, ``section_id``,
    ``show_when_empty``, ``is_enabled`` and ``sort_order``.
    """
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [card_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE cards SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_card(card_id: int) -> None:
    """Delete card with *card_id*."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM cards WHERE id=?", (card_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Item types
# ---------------------------------------------------------------------------
async def create_item_type(key: str, label_ar: str, label_en: str, *,
                           requires_lecture: bool = False,
                           allows_year: bool = True,
                           allows_lecturer: bool = True,
                           is_enabled: bool = True,
                           sort_order: int = 0) -> int:
    """Insert an item type and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO item_types
                (key, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                key,
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


async def get_item_type(key: str) -> tuple | None:
    """Return item type row for *key* or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, key, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order FROM item_types WHERE key=?",
            (key,),
        )
        return await cur.fetchone()


async def update_item_type(item_type_id: int, **fields) -> None:
    """Update an item type row with *fields*.

    Allowed keys: ``key``, ``label_ar``, ``label_en``, ``requires_lecture``,
    ``allows_year``, ``allows_lecturer``, ``is_enabled`` and ``sort_order``.
    """
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [item_type_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE item_types SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_item_type(item_type_id: int) -> None:
    """Delete item type with *item_type_id*."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM item_types WHERE id=?", (item_type_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Subject section enablement
# ---------------------------------------------------------------------------
async def set_subject_section_enable(subject_id: int, section_id: int,
                                    *, is_enabled: bool = True,
                                    sort_order: int = 0) -> None:
    """Upsert ``subject_section_enable`` row for *subject_id*/*section_id*."""
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
    """Return enabled sections for *subject_id* ordered by ``sort_order``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT section_id, is_enabled, sort_order FROM subject_section_enable WHERE subject_id=? ORDER BY sort_order",
            (subject_id,),
        )
        return await cur.fetchall()
