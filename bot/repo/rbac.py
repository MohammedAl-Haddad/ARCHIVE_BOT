"""Repository utilities for role based access control (RBAC)."""
from __future__ import annotations

import aiosqlite

from bot.db import base

async def create_admin(tg_user_id: int, name: str, role: str,
                       permissions_mask: int,
                       *, level_scope: str = "all",
                       is_active: bool = True) -> int:
    """Insert an admin account and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO admins (tg_user_id, name, role, permissions_mask, level_scope, is_active)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (tg_user_id, name, role, permissions_mask, level_scope, int(is_active)),
        )
        await db.commit()
        return cur.lastrowid


async def get_admin_by_user_id(tg_user_id: int) -> tuple | None:
    """Return admin row for Telegram ``user_id`` or ``None``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, tg_user_id, name, role, permissions_mask, level_scope, is_active FROM admins WHERE tg_user_id=?",
            (tg_user_id,),
        )
        return await cur.fetchone()


async def set_admin_active(tg_user_id: int, is_active: bool) -> None:
    """Enable or disable an admin account."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "UPDATE admins SET is_active=? WHERE tg_user_id=?",
            (int(is_active), tg_user_id),
        )
        await db.commit()


async def update_permissions(tg_user_id: int, permissions_mask: int) -> None:
    """Set the permissions mask for an admin."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "UPDATE admins SET permissions_mask=? WHERE tg_user_id=?",
            (permissions_mask, tg_user_id),
        )
        await db.commit()


async def has_permissions(tg_user_id: int, mask: int) -> bool:
    """Return ``True`` if admin ``tg_user_id`` has all permissions in *mask*.

    The check verifies that the admin exists, is active and that the
    provided mask bits are present in the stored ``permissions_mask``.
    """
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "SELECT permissions_mask, is_active FROM admins WHERE tg_user_id=?",
            (tg_user_id,),
        )
        row = await cur.fetchone()
        if row is None or not row[1]:
            return False
        return (row[0] & mask) == mask
