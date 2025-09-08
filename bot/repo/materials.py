"""Repository helpers for material records.

These functions expose a minimal CRUD interface for the ``materials``
table using the new dynamic-taxonomy columns ``section_id``,
``category_id`` and ``item_type_id``.  Only a small subset of the
production queries is implemented which is sufficient for unit tests
and for handlers that merely need basic persistence.
"""
from __future__ import annotations

from . import connect, translate_errors

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
async def get_material(material_id: int) -> tuple | None:
    """جلب صف المادة أو ``None`` | Return material row or ``None``.

    Args:
        material_id: معرف المادة / material id.

    Returns:
        tuple | None: صف المادة / material row.

    Raises:
        RepoError: عند حدوث خطأ في قاعدة البيانات.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT * FROM materials WHERE id=?",
            (material_id,),
        )
        return await cur.fetchone()


@translate_errors
async def update_material_storage(
    material_id: int,
    chat_id: int,
    msg_id: int,
    *,
    file_unique_id: str | None = None,
) -> None:
    """تحديث معلومات التخزين للمادة | Update storage identifiers.

    Args:
        material_id: معرف المادة / material id.
        chat_id: معرف الدردشة / chat id.
        msg_id: معرف الرسالة / message id.
        file_unique_id: معرف الملف أو ``None``.

    Raises:
        RepoError: أخطاء قاعدة البيانات / DB errors.
    """

    async with connect() as db:
        await db.execute(
            "UPDATE materials SET tg_storage_chat_id=?, tg_storage_msg_id=?, file_unique_id=? WHERE id=?",
            (chat_id, msg_id, file_unique_id, material_id),
        )
        await db.commit()


@translate_errors
async def delete_material(material_id: int) -> None:
    """حذف سجل مادة | Delete a material record.

    Args:
        material_id: معرف المادة / material id.

    Raises:
        RepoError: عند فشل قاعدة البيانات.
    """

    async with connect() as db:
        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()


@translate_errors
async def find_by_hash(content_hash: str) -> tuple | None:
    """البحث عن مادة ببصمة المحتوى | Find material by content hash.

    Args:
        content_hash: البصمة المراد البحث عنها / hash to search.

    Returns:
        tuple | None: صف المادة أو ``None`` / material row or ``None``.

    Raises:
        RepoError: أخطاء قاعدة البيانات / DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT * FROM materials WHERE content_hash=?",
            (content_hash,),
        )
        return await cur.fetchone()
