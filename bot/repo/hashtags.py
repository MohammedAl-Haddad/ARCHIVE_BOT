"""Repository helpers for hashtag aliasing and mappings."""
from __future__ import annotations

import aiosqlite

from bot.db import base

# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------
async def create_alias(alias: str, normalized: str, *, lang: str | None = None) -> int:
    """Insert a new alias and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO hashtag_aliases (alias, normalized, lang) VALUES (?, ?, ?)",
            (alias, normalized, lang),
        )
        await db.commit()
        return cur.lastrowid


async def get_alias(alias: str) -> tuple | None:
    """Return alias row for *alias* or ``None`` if missing."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, alias, normalized, lang FROM hashtag_aliases WHERE alias=?",
            (alias,),
        )
        return await cur.fetchone()


async def update_alias(alias_id: int, **fields) -> None:
    """Update an alias row with supplied *fields*."""
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [alias_id]
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(f"UPDATE hashtag_aliases SET {cols} WHERE id=?", params)
        await db.commit()


async def delete_alias(alias_id: int) -> None:
    """Delete alias with id *alias_id*."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("DELETE FROM hashtag_aliases WHERE id=?", (alias_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
async def create_mapping(alias_id: int, target_kind: str, target_id: int, *,
                         is_content_tag: bool = False,
                         overrides: str | None = None) -> int:
    """Insert a mapping from an alias to a target entity."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO hashtag_mappings
                (alias_id, target_kind, target_id, is_content_tag, overrides)
                VALUES (?, ?, ?, ?, ?)""",
            (alias_id, target_kind, target_id, int(is_content_tag), overrides),
        )
        await db.commit()
        return cur.lastrowid


async def get_mappings_for_alias(alias: str) -> list[tuple]:
    """Return mapping rows for *alias* string."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """SELECT m.id, a.alias, m.target_kind, m.target_id, m.is_content_tag, m.overrides
                FROM hashtag_mappings m
                JOIN hashtag_aliases a ON a.id = m.alias_id
                WHERE a.alias=?""",
            (alias,),
        )
        return await cur.fetchall()


async def lookup_targets(alias: str) -> list[tuple[str, int]]:
    """Return ``(target_kind, target_id)`` pairs for *alias*.

    The lookup first resolves the alias then returns all mapped targets.
    """
    rows = await get_mappings_for_alias(alias)
    return [(r[2], r[3]) for r in rows]
