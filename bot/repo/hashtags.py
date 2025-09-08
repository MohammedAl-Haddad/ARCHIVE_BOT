"""Repository helpers for hashtag aliasing and mappings."""
from __future__ import annotations

from . import connect, translate_errors

# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------
@translate_errors
async def create_alias(alias: str, normalized: str, *, lang: str | None = None) -> int:
    """إضافة اسم بديل وإرجاع معرفه | Insert alias and return its id.

    Args:
        alias: الاسم الأصلي / original alias.
        normalized: الاسم المعياري / normalized form.
        lang: رمز اللغة أو ``None``.

    Returns:
        int: المعرف الجديد / new row id.

    Raises:
        RepoConstraintError: عند تعارض القيود / on constraint conflict.
        RepoError: أخطاء قاعدة البيانات الأخرى / other DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO hashtag_aliases (alias, normalized, lang) VALUES (?, ?, ?)",
            (alias, normalized, lang),
        )
        await db.commit()
        return cur.lastrowid


@translate_errors
async def get_alias(alias: str) -> tuple | None:
    """الحصول على صف الاسم أو ``None`` | Return alias row or ``None``.

    Args:
        alias: النص المطلوب / alias string.

    Returns:
        tuple | None: صف قاعدة البيانات أو ``None`` / DB row or ``None``.

    Raises:
        RepoError: عند فشل الاتصال أو الاستعلام / on DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT id, alias, normalized, lang FROM hashtag_aliases WHERE alias=?",
            (alias,),
        )
        return await cur.fetchone()


@translate_errors
async def update_alias(alias_id: int, **fields) -> None:
    """تحديث صف اسم بديل | Update alias row.

    Args:
        alias_id: معرف الصف / row id.
        **fields: الحقول المعدلة / fields to update.

    Raises:
        RepoError: أخطاء قاعدة البيانات / DB errors.
    """

    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [alias_id]
    async with connect() as db:
        await db.execute(f"UPDATE hashtag_aliases SET {cols} WHERE id=?", params)
        await db.commit()


@translate_errors
async def delete_alias(alias_id: int) -> None:
    """حذف الاسم بالمعرف | Delete alias by id.

    Args:
        alias_id: معرف الصف / row id.

    Raises:
        RepoError: عند حدوث خطأ في قاعدة البيانات / DB error.
    """

    async with connect() as db:
        await db.execute("DELETE FROM hashtag_aliases WHERE id=?", (alias_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
@translate_errors
async def create_mapping(
    alias_id: int,
    target_kind: str,
    target_id: int,
    *,
    is_content_tag: bool = False,
    overrides: str | None = None,
) -> int:
    """ربط اسم بكيان آخر | Map alias to target.

    Args:
        alias_id: معرف الاسم / alias id.
        target_kind: نوع الهدف / target kind.
        target_id: معرف الهدف / target id.
        is_content_tag: هل هو وسم محتوى؟ / content tag flag.
        overrides: بيانات إضافية / override data.

    Returns:
        int: معرف الربط / mapping id.

    Raises:
        RepoConstraintError: عند فشل القيود / on constraint conflict.
        RepoError: أخطاء قاعدة البيانات الأخرى / other DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO hashtag_mappings
                (alias_id, target_kind, target_id, is_content_tag, overrides)
                VALUES (?, ?, ?, ?, ?)""",
            (alias_id, target_kind, target_id, int(is_content_tag), overrides),
        )
        await db.commit()
        return cur.lastrowid


@translate_errors
async def get_mappings_for_alias(alias: str) -> list[tuple]:
    """إرجاع كل الربوط للاسم | Return mapping rows for alias.

    Args:
        alias: النص المطلوب / alias string.

    Returns:
        list[tuple]: قائمة الربوط / list of mappings.

    Raises:
        RepoError: أخطاء قاعدة البيانات / DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            """SELECT m.id, a.alias, m.target_kind, m.target_id, m.is_content_tag, m.overrides
                FROM hashtag_mappings m
                JOIN hashtag_aliases a ON a.id = m.alias_id
                WHERE a.alias=?""",
            (alias,),
        )
        return await cur.fetchall()


@translate_errors
async def lookup_targets(alias: str) -> list[tuple[str, int]]:
    """الحصول على أهداف الاسم | Return ``(target_kind, target_id)`` pairs.

    Args:
        alias: الاسم المراد البحث عنه / alias to resolve.

    Returns:
        list[tuple[str, int]]: أزواج الهدف / target pairs.

    Raises:
        RepoError: عند فشل العمليات / DB errors.
    """

    rows = await get_mappings_for_alias(alias)
    return [(r[2], r[3]) for r in rows]
