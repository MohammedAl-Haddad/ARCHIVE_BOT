"""Repository utilities for role based access control (RBAC).

This module provides a minimal role/permission system. Roles may have tags
which can be used to broadcast messages to all members of a classification.
Permissions can optionally be scoped to a JSON object (e.g. limiting a role to
manage a specific group)."""
from __future__ import annotations

import json
from typing import Any

from . import RepoNotFound, connect, translate_errors


def _role_from_row(row: tuple[Any, ...]) -> dict:
    """Convert a DB row to a role dictionary."""

    return {
        "id": row[0],
        "name": row[1],
        "tags": json.loads(row[2] or "[]"),
        "is_enabled": bool(row[3]),
    }


@translate_errors
async def create_role(
    name: str,
    tags: list[str] | None = None,
    *,
    is_enabled: bool = True,
) -> dict:
    """إنشاء دور جديد | Create a role and return its data."""

    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO roles (name, tags, is_enabled) VALUES (?, ?, ?)",
            (name, json.dumps(tags or []), int(is_enabled)),
        )
        await db.commit()
        role_id = cur.lastrowid
    return {
        "id": role_id,
        "name": name,
        "tags": tags or [],
        "is_enabled": is_enabled,
    }


@translate_errors
async def get_role(role_id: int, *, is_enabled: bool | None = True) -> dict:
    """Return a role by id respecting ``is_enabled`` filter."""

    query = "SELECT id, name, tags, is_enabled FROM roles WHERE id=?"
    params: list[Any] = [role_id]
    if is_enabled is True:
        query += " AND is_enabled=1"
    elif is_enabled is False:
        query += " AND is_enabled=0"
    async with connect() as db:
        cur = await db.execute(query, params)
        row = await cur.fetchone()
    if row is None:
        raise RepoNotFound("role not found")
    return _role_from_row(row)


@translate_errors
async def list_roles(is_enabled: bool | None = True) -> list[dict]:
    """List roles optionally filtered by ``is_enabled``."""

    query = "SELECT id, name, tags, is_enabled FROM roles"
    if is_enabled is True:
        query += " WHERE is_enabled=1"
    elif is_enabled is False:
        query += " WHERE is_enabled=0"
    async with connect() as db:
        cur = await db.execute(query)
        rows = await cur.fetchall()
    return [_role_from_row(row) for row in rows]


@translate_errors
async def update_role(
    role_id: int,
    *,
    name: str | None = None,
    tags: list[str] | None = None,
    is_enabled: bool | None = None,
    current_is_enabled: bool | None = True,
) -> dict:
    """Update role fields and return updated record."""

    sets: list[str] = []
    params: list[Any] = []
    if name is not None:
        sets.append("name=?")
        params.append(name)
    if tags is not None:
        sets.append("tags=?")
        params.append(json.dumps(tags))
    if is_enabled is not None:
        sets.append("is_enabled=?")
        params.append(int(is_enabled))
    if not sets:
        return await get_role(role_id, is_enabled=current_is_enabled)

    params.append(role_id)
    query = f"UPDATE roles SET {', '.join(sets)} WHERE id=?"
    if current_is_enabled is True:
        query += " AND is_enabled=1"
    elif current_is_enabled is False:
        query += " AND is_enabled=0"

    async with connect() as db:
        cur = await db.execute(query, params)
        if cur.rowcount == 0:
            raise RepoNotFound("role not found")
        await db.commit()

    return await get_role(role_id, is_enabled=None)


@translate_errors
async def delete_role(role_id: int, *, is_enabled: bool | None = True) -> dict:
    """Delete a role respecting ``is_enabled`` filter."""

    query = "DELETE FROM roles WHERE id=?"
    params: list[Any] = [role_id]
    if is_enabled is True:
        query += " AND is_enabled=1"
    elif is_enabled is False:
        query += " AND is_enabled=0"
    async with connect() as db:
        cur = await db.execute(query, params)
        await db.commit()
    if cur.rowcount == 0:
        raise RepoNotFound("role not found")
    return {"id": role_id}


@translate_errors
async def assign_role(user_id: int, role_id: int) -> dict:
    """إسناد دور لمستخدم | Assign ``role_id`` to ``user_id``."""

    # Ensure role is enabled
    await get_role(role_id)
    async with connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
        await db.commit()
    return {"user_id": user_id, "role_id": role_id}


@translate_errors
async def revoke_role(user_id: int, role_id: int) -> dict:
    """إزالة دور من مستخدم | Remove ``role_id`` from ``user_id``."""

    async with connect() as db:
        await db.execute(
            "DELETE FROM user_roles WHERE user_id=? AND role_id=? AND EXISTS (SELECT 1 FROM roles r WHERE r.id=? AND r.is_enabled=1)",
            (user_id, role_id, role_id),
        )
        await db.commit()
    return {"user_id": user_id, "role_id": role_id}


@translate_errors
async def list_user_roles(user_id: int, *, is_enabled: bool | None = True) -> list[dict]:
    """List roles assigned to ``user_id``."""

    query = (
        "SELECT r.id, r.name, r.tags, r.is_enabled FROM user_roles ur "
        "JOIN roles r ON ur.role_id = r.id WHERE ur.user_id=?"
    )
    params: list[Any] = [user_id]
    if is_enabled is True:
        query += " AND r.is_enabled=1"
    elif is_enabled is False:
        query += " AND r.is_enabled=0"
    async with connect() as db:
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
    return [_role_from_row(row) for row in rows]


@translate_errors
async def set_permission(role_id: int, permission_key: str, scope: dict | None = None) -> dict:
    """تعيين صلاحية لدور | Set a permission for a role."""

    await get_role(role_id)
    async with connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO role_permissions (role_id, permission_key, scope) VALUES (?, ?, ?)",
            (role_id, permission_key, json.dumps(scope)),
        )
        await db.commit()
    return {"role_id": role_id, "permission_key": permission_key, "scope": scope}


@translate_errors
async def list_role_permissions(role_id: int, *, is_enabled: bool | None = True) -> list[dict]:
    """List permissions for a role."""

    query = (
        "SELECT rp.permission_key, rp.scope FROM role_permissions rp "
        "JOIN roles r ON rp.role_id = r.id WHERE rp.role_id=?"
    )
    params: list[Any] = [role_id]
    if is_enabled is True:
        query += " AND r.is_enabled=1"
    elif is_enabled is False:
        query += " AND r.is_enabled=0"
    async with connect() as db:
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
    return [
        {
            "role_id": role_id,
            "permission_key": key,
            "scope": json.loads(scope) if scope else None,
        }
        for key, scope in rows
    ]


@translate_errors
async def delete_permission(role_id: int, permission_key: str, *, is_enabled: bool | None = True) -> dict:
    """Remove a permission from a role."""

    query = "DELETE FROM role_permissions WHERE role_id=? AND permission_key=?"
    params: list[Any] = [role_id, permission_key]
    if is_enabled is True:
        query += " AND EXISTS (SELECT 1 FROM roles r WHERE r.id=? AND r.is_enabled=1)"
        params.append(role_id)
    elif is_enabled is False:
        query += " AND EXISTS (SELECT 1 FROM roles r WHERE r.id=? AND r.is_enabled=0)"
        params.append(role_id)
    async with connect() as db:
        await db.execute(query, params)
        await db.commit()
    return {"role_id": role_id, "permission_key": permission_key}


@translate_errors
async def has_permission(
    user_id: int,
    permission_key: str,
    scope: dict | None = None,
    *,
    is_enabled: bool = True,
) -> bool:
    """تحقق من صلاحية مستخدم | Return True if user has permission."""

    query = (
        "SELECT rp.scope FROM user_roles ur "
        "JOIN role_permissions rp ON ur.role_id = rp.role_id "
        "JOIN roles r ON r.id = rp.role_id "
        "WHERE ur.user_id=? AND rp.permission_key=?"
    )
    params: list[Any] = [user_id, permission_key]
    if is_enabled:
        query += " AND r.is_enabled=1"
    async with connect() as db:
        cur = await db.execute(query, params)
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


@translate_errors
async def users_with_tag(tag: str, *, is_enabled: bool = True) -> list[int]:
    """إرجاع المستخدمين حسب الوسم | Return user ids for roles tagged with ``tag``."""

    query = (
        "SELECT DISTINCT ur.user_id FROM roles r "
        "JOIN user_roles ur ON r.id = ur.role_id "
        "JOIN json_each(r.tags) jt WHERE jt.value = ?"
    )
    params: list[Any] = [tag]
    if is_enabled:
        query += " AND r.is_enabled = 1"
    async with connect() as db:
        cur = await db.execute(query, params)
        return [row[0] for row in await cur.fetchall()]


@translate_errors
async def broadcast(tag: str, message: str, send_func) -> int:
    """بث رسالة لمستخدمين بوسم معين | Broadcast message to tagged users.

    Args:
        tag: الوسم المطلوب / tag value.
        message: الرسالة / message text.
        send_func: دالة الإرسال ``(user_id, message)``.

    Returns:
        int: عدد المستخدمين المرسَل إليهم / number of recipients.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    user_ids = await users_with_tag(tag)
    for uid in user_ids:
        await send_func(uid, message)
    return len(user_ids)


__all__ = [
    "create_role",
    "get_role",
    "list_roles",
    "update_role",
    "delete_role",
    "assign_role",
    "list_user_roles",
    "revoke_role",
    "set_permission",
    "list_role_permissions",
    "delete_permission",
    "has_permission",
    "broadcast",
    "users_with_tag",
]
