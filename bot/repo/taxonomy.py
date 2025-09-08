"""Helpers for managing the dynamic taxonomy tables using id-based lookups."""
from __future__ import annotations

from . import connect, translate_errors

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
@translate_errors
async def create_section(
    label_ar: str,
    label_en: str,
    *,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> int:
    """إنشاء قسم جديد | Insert a new section and return its id.

    Args:
        label_ar: الاسم بالعربية / Arabic label.
        label_en: الاسم بالإنجليزية / English label.
        is_enabled: هل هو مفعّل؟ / enabled flag.
        sort_order: ترتيب العرض / sort order.

    Returns:
        int: معرف القسم / section id.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO sections (label_ar, label_en, is_enabled, sort_order) VALUES (?, ?, ?, ?)",
            (label_ar, label_en, int(is_enabled), sort_order),
        )
        await db.commit()
        return cur.lastrowid


@translate_errors
async def get_section(section_id: int) -> tuple | None:
    """جلب صف القسم أو ``None`` | Return section row or ``None``.

    Args:
        section_id: معرف القسم / section id.

    Returns:
        tuple | None: صف القسم / section row.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT id, label_ar, label_en, is_enabled, sort_order, created_at, updated_at FROM sections WHERE id=?",
            (section_id,),
        )
        return await cur.fetchone()


@translate_errors
async def update_section(section_id: int, **fields) -> None:
    """تحديث بيانات قسم | Update a section with given fields.

    Args:
        section_id: معرف القسم / section id.
        **fields: الحقول المعدلة / fields to update.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [section_id]
    async with connect() as db:
        await db.execute(f"UPDATE sections SET {cols} WHERE id=?", params)
        await db.commit()


@translate_errors
async def delete_section(section_id: int) -> None:
    """حذف قسم بالمعرف | Delete section by id.

    Args:
        section_id: معرف القسم / section id.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute("DELETE FROM sections WHERE id=?", (section_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Cards (material categories)
# ---------------------------------------------------------------------------
@translate_errors
async def create_card(
    label_ar: str,
    label_en: str,
    *,
    section_id: int | None = None,
    show_when_empty: bool = False,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> int:
    """إنشاء بطاقة مادة | Insert a card (category) and return its id.

    Args:
        label_ar: الاسم بالعربية.
        label_en: الاسم بالإنجليزية.
        section_id: معرف القسم أو ``None``.
        show_when_empty: إظهار حتى لو فارغة؟
        is_enabled: حالة التفعيل.
        sort_order: ترتيب العرض.

    Returns:
        int: معرف البطاقة.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
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


@translate_errors
async def get_card(card_id: int) -> tuple | None:
    """جلب صف بطاقة أو ``None`` | Return card row or ``None``.

    Args:
        card_id: معرف البطاقة.

    Returns:
        tuple | None: صف البطاقة.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            """SELECT id, section_id, label_ar, label_en, show_when_empty,
                       is_enabled, sort_order, created_at, updated_at
                   FROM cards WHERE id=?""",
            (card_id,),
        )
        return await cur.fetchone()


@translate_errors
async def update_card(card_id: int, **fields) -> None:
    """تحديث بطاقة | Update card with fields.

    Args:
        card_id: معرف البطاقة.
        **fields: الحقول المعدلة.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [card_id]
    async with connect() as db:
        await db.execute(f"UPDATE cards SET {cols} WHERE id=?", params)
        await db.commit()


@translate_errors
async def delete_card(card_id: int) -> None:
    """حذف بطاقة بالمعرف | Delete card by id.

    Args:
        card_id: معرف البطاقة.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute("DELETE FROM cards WHERE id=?", (card_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Item types
# ---------------------------------------------------------------------------
@translate_errors
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
    """إنشاء نوع عنصر | Insert an item type and return its id.

    Args:
        label_ar: الاسم بالعربية.
        label_en: الاسم بالإنجليزية.
        requires_lecture: هل يتطلب محاضرة؟
        allows_year: يسمح بالسنة؟
        allows_lecturer: يسمح بالمحاضر؟
        is_enabled: حالة التفعيل.
        sort_order: ترتيب العرض.

    Returns:
        int: معرف النوع.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
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


@translate_errors
async def get_item_type(item_type_id: int) -> tuple | None:
    """جلب صف نوع عنصر أو ``None`` | Return item type row or ``None``.

    Args:
        item_type_id: معرف النوع.

    Returns:
        tuple | None: صف النوع.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            """SELECT id, label_ar, label_en, requires_lecture, allows_year,
                       allows_lecturer, is_enabled, sort_order, created_at, updated_at
                   FROM item_types WHERE id=?""",
            (item_type_id,),
        )
        return await cur.fetchone()


@translate_errors
async def update_item_type(item_type_id: int, **fields) -> None:
    """تحديث نوع عنصر | Update item type with fields.

    Args:
        item_type_id: معرف النوع.
        **fields: الحقول المعدلة.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [item_type_id]
    async with connect() as db:
        await db.execute(f"UPDATE item_types SET {cols} WHERE id=?", params)
        await db.commit()


@translate_errors
async def delete_item_type(item_type_id: int) -> None:
    """حذف نوع عنصر | Delete item type by id.

    Args:
        item_type_id: معرف النوع.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute("DELETE FROM item_types WHERE id=?", (item_type_id,))
        await db.commit()

# ---------------------------------------------------------------------------
# Subject section enablement
# ---------------------------------------------------------------------------
@translate_errors
async def set_subject_section_enable(
    subject_id: int,
    section_id: int,
    *,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> None:
    """تفعيل قسم لمادة | Upsert subject-section enable row.

    Args:
        subject_id: معرف المادة.
        section_id: معرف القسم.
        is_enabled: حالة التفعيل.
        sort_order: ترتيب العرض.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute(
            """INSERT INTO subject_section_enable
                (subject_id, section_id, is_enabled, sort_order)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subject_id, section_id)
                DO UPDATE SET is_enabled=excluded.is_enabled, sort_order=excluded.sort_order""",
            (subject_id, section_id, int(is_enabled), sort_order),
        )
        await db.commit()


@translate_errors
async def get_enabled_sections_for_subject(subject_id: int) -> list[tuple]:
    """الأقسام المفعلة لمادة | Return enabled sections for a subject.

    Args:
        subject_id: معرف المادة.

    Returns:
        list[tuple]: قائمة الأقسام.

    Raises:
        RepoError: أخطاء قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT section_id, is_enabled, sort_order FROM subject_section_enable WHERE subject_id=? ORDER BY sort_order",
            (subject_id,),
        )
        return await cur.fetchall()
