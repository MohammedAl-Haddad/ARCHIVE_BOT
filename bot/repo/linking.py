"""Repository helpers for linking Telegram entities to subjects and sections."""
from __future__ import annotations

from . import RepoNotFound, connect, translate_errors

@translate_errors
async def upsert_group(
    tg_chat_id: int,
    title: str,
    *,
    level_id: int | None = None,
    term_id: int | None = None,
    section_id: int | None = None,
) -> int:
    """إضافة/تحديث مجموعة | Insert or update a group.

    Args:
        tg_chat_id: معرف الدردشة / chat identifier.
        title: عنوان المجموعة / group title.
        level_id: معرف المستوى أو ``None``.
        term_id: معرف الفصل أو ``None``.
        section_id: معرف الشعبة أو ``None``.

    Returns:
        int: معرف المجموعة / group id.

    Raises:
        RepoConstraintError: عند فشل القيود / on constraint issues.
        RepoNotFound: إذا تعذر إيجاد السجل بعد التحديث / if record missing.
        RepoError: أخطاء قاعدة البيانات / other DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO groups (tg_chat_id, title, level_id, term_id, section_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tg_chat_id) DO UPDATE SET
                    title=excluded.title,
                    level_id=excluded.level_id,
                    term_id=excluded.term_id,
                    section_id=excluded.section_id""",
            (tg_chat_id, title, level_id, term_id, section_id),
        )
        await db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        cur = await db.execute(
            "SELECT id FROM groups WHERE tg_chat_id=?",
            (tg_chat_id,),
        )
        row = await cur.fetchone()
        if row is None:
            raise RepoNotFound(f"group {tg_chat_id!r} not found")
        return row[0]


@translate_errors
async def get_group(tg_chat_id: int) -> tuple | None:
    """إرجاع صف المجموعة أو ``None`` | Return group row or ``None``.

    Args:
        tg_chat_id: معرف الدردشة / chat identifier.

    Returns:
        tuple | None: صف المجموعة / group row.

    Raises:
        RepoError: خطأ قاعدة البيانات / DB error.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT id, tg_chat_id, title, level_id, term_id, section_id FROM groups WHERE tg_chat_id=?",
            (tg_chat_id,),
        )
        return await cur.fetchone()


@translate_errors
async def upsert_topic(
    group_id: int,
    tg_topic_id: int,
    subject_id: int,
    *,
    section_id: int | None = None,
) -> int:
    """إضافة/تحديث موضوع | Insert or update a topic mapping.

    Args:
        group_id: معرف المجموعة / group id.
        tg_topic_id: معرف موضوع تيليغرام / Telegram topic id.
        subject_id: معرف المادة / subject id.
        section_id: معرف الشعبة أو ``None``.

    Returns:
        int: معرف الموضوع / topic id.

    Raises:
        RepoConstraintError: عند فشل القيود.
        RepoNotFound: إذا لم يوجد السجل.
        RepoError: أخطاء قاعدة البيانات الأخرى.
    """

    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO topics (group_id, tg_topic_id, subject_id, section_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(group_id, tg_topic_id) DO UPDATE SET
                    subject_id=excluded.subject_id,
                    section_id=excluded.section_id""",
            (group_id, tg_topic_id, subject_id, section_id),
        )
        await db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        cur = await db.execute(
            "SELECT id FROM topics WHERE group_id=? AND tg_topic_id=?",
            (group_id, tg_topic_id),
        )
        row = await cur.fetchone()
        if row is None:
            raise RepoNotFound("topic not found")
        return row[0]


@translate_errors
async def get_topic(group_id: int, tg_topic_id: int) -> tuple | None:
    """إرجاع صف الموضوع أو ``None`` | Return topic row or ``None``.

    Args:
        group_id: معرف المجموعة / group id.
        tg_topic_id: معرف موضوع تيليغرام / Telegram topic id.

    Returns:
        tuple | None: صف الموضوع / topic row.

    Raises:
        RepoError: أخطاء قاعدة البيانات / DB errors.
    """

    async with connect() as db:
        cur = await db.execute(
            "SELECT id, group_id, tg_topic_id, subject_id, section_id FROM topics WHERE group_id=? AND tg_topic_id=?",
            (group_id, tg_topic_id),
        )
        return await cur.fetchone()
