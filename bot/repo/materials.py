"""Repository helpers for material records.

These functions expose a minimal CRUD interface for the ``materials``
table using the new dynamic-taxonomy columns ``section_id``,
``category_id`` and ``item_type_id``.  Only a small subset of the
production queries is implemented which is sufficient for unit tests
and for handlers that merely need basic persistence.
"""
from __future__ import annotations

from . import connect, translate_errors, RepoConstraintError

# Column order helper used to map rows to dictionaries
_MATERIAL_FIELDS = [
    "id",
    "subject_id",
    "section_id",
    "category_id",
    "item_type_id",
    "title",
    "url",
    "year_id",
    "lecturer_id",
    "lecture_no",
    "content_hash",
    "tg_storage_chat_id",
    "tg_storage_msg_id",
    "file_unique_id",
    "source_chat_id",
    "source_topic_id",
    "source_message_id",
    "created_by_admin_id",
]


def _row_to_dict(row: tuple | None) -> dict | None:
    """Convert a material row tuple to a dictionary."""

    if row is None:
        return None
    return dict(zip(_MATERIAL_FIELDS, row))

@translate_errors
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
    """إضافة مادة وإرجاع معرفها | Insert material and return its id.

    Args:
        subject_id: معرف المادة / subject id.
        section_id: معرف القسم أو ``None``.
        category_id: معرف التصنيف أو ``None``.
        item_type_id: نوع العنصر أو ``None``.
        title: العنوان / title text.
        url: رابط أو ``None``.
        year_id: معرف السنة أو ``None``.
        lecturer_id: معرف المحاضر أو ``None``.
        lecture_no: رقم المحاضرة أو ``None``.
        content_hash: بصمة المحتوى أو ``None``.
        tg_storage_chat_id: معرف التخزين في تيليغرام أو ``None``.
        tg_storage_msg_id: رسالة التخزين أو ``None``.
        file_unique_id: معرف الملف أو ``None``.
        source_chat_id: معرف المصدر أو ``None``.
        source_topic_id: موضوع المصدر أو ``None``.
        source_message_id: رسالة المصدر أو ``None``.
        created_by_admin_id: معرف المسؤول أو ``None``.

    Returns:
        int: معرف السجل / new row id.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoError: أخطاء قاعدة البيانات.
    """

    # Ensure that exactly one of category_id or item_type_id is provided
    if (category_id is None) == (item_type_id is None):
        raise RepoConstraintError("either category_id or item_type_id must be set")

    async with connect() as db:
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


@translate_errors
async def get_material(material_id: int) -> dict | None:
    """جلب صف المادة أو ``None`` | Return material as dict or ``None``.

    Args:
        material_id: معرف المادة / material id.

    Returns:
        dict | None: صف المادة / material row.

    Raises:
        RepoError: عند حدوث خطأ في قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            f"SELECT {', '.join(_MATERIAL_FIELDS)} FROM materials WHERE id=?",
            (material_id,),
        )
        row = await cur.fetchone()

    return _row_to_dict(row)


@translate_errors
async def update_material(material_id: int, **fields) -> dict | None:
    """Update fields of a material and return the updated row."""

    if not fields:
        return await get_material(material_id)

    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [material_id]
    async with connect() as db:
        await db.execute(f"UPDATE materials SET {cols} WHERE id=?", params)
        await db.commit()

    return await get_material(material_id)


@translate_errors
async def update_material_storage(
    material_id: int,
    chat_id: int,
    msg_id: int,
    *,
    file_unique_id: str | None = None,
) -> dict | None:
    """تحديث معلومات التخزين للمادة | Update storage identifiers."""

    return await update_material(
        material_id,
        tg_storage_chat_id=chat_id,
        tg_storage_msg_id=msg_id,
        file_unique_id=file_unique_id,
    )


@translate_errors
async def delete_material(material_id: int) -> dict | None:
    """حذف سجل مادة | Delete a material record and return it."""

    row = await get_material(material_id)
    if row is None:
        return None

    async with connect() as db:
        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()

    return row


@translate_errors
async def find_by_hash(content_hash: str) -> dict | None:
    """البحث عن مادة ببصمة المحتوى | Find material by content hash."""

    async with connect() as db:
        cur = await db.execute(
            f"SELECT {', '.join(_MATERIAL_FIELDS)} FROM materials WHERE content_hash=?",
            (content_hash,),
        )
        row = await cur.fetchone()

    return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Enumeration and listing helpers
# ---------------------------------------------------------------------------


@translate_errors
async def count_by_subject(subject_id: int) -> int:
    """Return number of materials for a subject."""

    async with connect() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM materials WHERE subject_id=?",
            (subject_id,),
        )
        (count,) = await cur.fetchone()
    return count


@translate_errors
async def count_by_section(subject_id: int, section_id: int) -> int:
    """Return number of materials for a subject-section pair."""

    async with connect() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM materials WHERE subject_id=? AND section_id=?",
            (subject_id, section_id),
        )
        (count,) = await cur.fetchone()
    return count


@translate_errors
async def count_by_item_type(
    subject_id: int, section_id: int, item_type_id: int
) -> int:
    """Return number of materials for a subject-section-item_type tuple."""

    async with connect() as db:
        cur = await db.execute(
            """
            SELECT COUNT(*) FROM materials
            WHERE subject_id=? AND section_id=? AND item_type_id=?
            """,
            (subject_id, section_id, item_type_id),
        )
        (count,) = await cur.fetchone()
    return count


@translate_errors
async def get_materials(
    subject_id: int,
    *,
    section_id: int | None = None,
    item_type_id: int | None = None,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    lecture_no: int | None = None,
    include_disabled: bool = False,
) -> list[dict]:
    """Return materials filtered by various attributes."""

    cols = ", ".join(f"m.{c}" for c in _MATERIAL_FIELDS)
    query = f"""
        SELECT {cols} FROM materials AS m
        LEFT JOIN subject_section_enable AS sse
            ON sse.subject_id = m.subject_id AND sse.section_id = m.section_id
        LEFT JOIN sections AS s ON s.id = m.section_id
        LEFT JOIN cards AS c ON c.id = m.category_id
        LEFT JOIN section_item_types AS sit
            ON sit.section_id = m.section_id AND sit.item_type_id = m.item_type_id
        LEFT JOIN item_types AS it ON it.id = m.item_type_id
        WHERE m.subject_id=?
    """
    params: list[int | str | None] = [subject_id]
    if section_id is not None:
        query += " AND m.section_id=?"
        params.append(section_id)
    if item_type_id is not None:
        query += " AND m.item_type_id=?"
        params.append(item_type_id)
    if year_id is not None:
        query += " AND m.year_id=?"
        params.append(year_id)
    if lecturer_id is not None:
        query += " AND m.lecturer_id=?"
        params.append(lecturer_id)
    if lecture_no is not None:
        query += " AND m.lecture_no=?"
        params.append(lecture_no)
    if not include_disabled:
        query += (
            " AND (s.is_enabled=1 OR s.id IS NULL)"
            " AND (c.is_enabled=1 OR c.id IS NULL)"
            " AND (it.is_enabled=1 OR it.id IS NULL)"
            " AND (sse.is_enabled=1 OR sse.subject_id IS NULL)"
            " AND (sit.is_enabled=1 OR sit.section_id IS NULL)"
        )

    async with connect() as db:
        cur = await db.execute(query, params)
        rows = await cur.fetchall()

    return [_row_to_dict(r) for r in rows]
