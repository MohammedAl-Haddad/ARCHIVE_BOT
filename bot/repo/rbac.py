"""Repository utilities for role based access control (RBAC).

This module provides a minimal role/permission system. Roles may have tags
which can be used to broadcast messages to all members of a classification.
Permissions can optionally be scoped to a JSON object (e.g. limiting a role to
manage a specific group)."""
from __future__ import annotations

import json
import aiosqlite

from bot.db import base


async def create_role(name: str, tags: list[str] | None = None, *, is_enabled: bool = True) -> int:
    """Create a role and return its id."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO roles (name, tags, is_enabled) VALUES (?, ?, ?)",
            (name, json.dumps(tags or []), int(is_enabled)),
        )
        await db.commit()
        return cur.lastrowid


async def assign_role(user_id: int, role_id: int) -> None:
    """Assign ``role_id`` to ``user_id``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
        await db.commit()


async def revoke_role(user_id: int, role_id: int) -> None:
    """Remove ``role_id`` from ``user_id``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_roles WHERE user_id=? AND role_id=?",
            (user_id, role_id),
        )
        await db.commit()


async def set_permission(role_id: int, permission_key: str, scope: dict | None = None) -> None:
    """Set a permission for a role.

    ``scope`` is stored as JSON and may be used to restrict the permission to a
    specific context such as a group or topic."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO role_permissions (role_id, permission_key, scope) VALUES (?, ?, ?)",
            (role_id, permission_key, json.dumps(scope)),
        )
        await db.commit()


async def has_permission(user_id: int, permission_key: str, scope: dict | None = None) -> bool:
    """Return True if ``user_id`` has ``permission_key`` with optional ``scope``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT rp.scope FROM user_roles ur
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN roles r ON r.id = rp.role_id
            WHERE ur.user_id=? AND rp.permission_key=? AND r.is_enabled=1
            """,
            (user_id, permission_key),
        )
        rows = await cur.fetchall()
        if not rows:
            return False
        if scope is None:
            return True
        for (scope_json,) in rows:
            if scope_json is None:
                return True
            stored = json.loads(scope_json)
            if all(stored.get(k) == v for k, v in scope.items()):
                return True
        return False


async def users_with_tag(tag: str) -> list[int]:
    """Return all user ids that belong to roles tagged with ``tag``."""
    async with aiosqlite.connect(base.DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT ur.user_id FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            JOIN json_each(r.tags) jt
            WHERE jt.value = ? AND r.is_enabled = 1
            """,
            (tag,),
        )
        return [row[0] for row in await cur.fetchall()]


async def broadcast(tag: str, message: str, send_func) -> int:
    """Send ``message`` to all users having roles tagged with ``tag``.

    ``send_func`` should be an awaitable accepting ``(user_id, message)``.
    The function returns the number of users the message was sent to."""
    user_ids = await users_with_tag(tag)
    for uid in user_ids:
        await send_func(uid, message)
    return len(user_ids)


__all__ = [
    "create_role",
    "assign_role",
    "revoke_role",
    "set_permission",
    "has_permission",
    "broadcast",
    "users_with_tag",
]
