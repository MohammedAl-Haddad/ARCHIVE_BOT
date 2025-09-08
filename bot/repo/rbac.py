"""Repository utilities for role based access control (RBAC).

This module provides a minimal role/permission system. Roles may have tags
which can be used to broadcast messages to all members of a classification.
Permissions can optionally be scoped to a JSON object (e.g. limiting a role to
manage a specific group)."""
from __future__ import annotations

import json

from . import connect, translate_errors


@translate_errors
async def create_role(
    name: str,
    tags: list[str] | None = None,
    *,
    is_enabled: bool = True,
) -> int:
    """إنشاء دور جديد | Create a role and return its id.

    Args:
        name: اسم الدور / role name.
        tags: وسوم اختيارية / optional tags.
        is_enabled: هل الدور مفعّل؟ / enabled flag.

    Returns:
        int: معرف الدور / role id.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO roles (name, tags, is_enabled) VALUES (?, ?, ?)",
            (name, json.dumps(tags or []), int(is_enabled)),
        )
        await db.commit()
        return cur.lastrowid


@translate_errors
async def assign_role(user_id: int, role_id: int) -> None:
    """إسناد دور لمستخدم | Assign ``role_id`` to ``user_id``.

    Args:
        user_id: معرف المستخدم / user id.
        role_id: معرف الدور / role id.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
        await db.commit()


@translate_errors
async def revoke_role(user_id: int, role_id: int) -> None:
    """إزالة دور من مستخدم | Remove ``role_id`` from ``user_id``.

    Args:
        user_id: معرف المستخدم / user id.
        role_id: معرف الدور / role id.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute(
            "DELETE FROM user_roles WHERE user_id=? AND role_id=?",
            (user_id, role_id),
        )
        await db.commit()


@translate_errors
async def set_permission(role_id: int, permission_key: str, scope: dict | None = None) -> None:
    """تعيين صلاحية لدور | Set a permission for a role.

    Args:
        role_id: معرف الدور / role id.
        permission_key: مفتاح الصلاحية / permission key.
        scope: نطاق اختياري بصيغة JSON / optional scope.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO role_permissions (role_id, permission_key, scope) VALUES (?, ?, ?)",
            (role_id, permission_key, json.dumps(scope)),
        )
        await db.commit()


@translate_errors
async def has_permission(user_id: int, permission_key: str, scope: dict | None = None) -> bool:
    """تحقق من صلاحية مستخدم | Return True if user has permission.

    Args:
        user_id: معرف المستخدم / user id.
        permission_key: مفتاح الصلاحية.
        scope: نطاق اختياري / optional scope.

    Returns:
        bool: ``True`` إذا كانت الصلاحية موجودة / True if allowed.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
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


@translate_errors
async def users_with_tag(tag: str) -> list[int]:
    """إرجاع المستخدمين حسب الوسم | Return user ids for roles tagged with ``tag``.

    Args:
        tag: الوسم المطلوب / tag value.

    Returns:
        list[int]: قائمة المعرفات / list of user ids.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
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
    "assign_role",
    "revoke_role",
    "set_permission",
    "has_permission",
    "broadcast",
    "users_with_tag",
]
