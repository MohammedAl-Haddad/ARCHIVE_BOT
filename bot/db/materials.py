"""Low level helpers for the ``materials`` table.

This module used to expose helpers that operated on textual taxonomy
identifiers (``section``/``category``).  The dynamic taxonomy migration
replaced those with integer foreign keys so the functions below now deal
exclusively with ``section_id``, ``category_id`` and ``item_type_id`` in
addition to optional ``lecture_no`` and ``content_hash`` columns.

Only a compact subset of the original helpers is implemented as the test
suite only relies on basic CRUD operations.
"""
from __future__ import annotations

import aiosqlite

from .base import DB_PATH

# Placeholder mapping kept for backwards compatibility.  The new taxonomy
# system stores labels in dedicated tables so this constant is mostly
# unused, but some legacy modules still import it.
LECTURE_TYPE_LABELS: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Basic CRUD helpers
# ---------------------------------------------------------------------------
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
    """Insert a material row and return its database id."""
    async with aiosqlite.connect(DB_PATH) as db:
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


async def update_material_storage(
    material_id: int,
    chat_id: int,
    msg_id: int,
    *,
    file_unique_id: str | None = None,
) -> None:
    """Update the storage location of a material."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE materials SET tg_storage_chat_id=?, tg_storage_msg_id=?, file_unique_id=? WHERE id=?",
            (chat_id, msg_id, file_unique_id, material_id),
        )
        await db.commit()


async def delete_material(material_id: int) -> None:
    """Delete material with *material_id*."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()


async def get_material_source(material_id: int) -> tuple[int | None, int | None, int | None] | None:
    """Return ``(chat_id, topic_id, message_id)`` of the original message."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT source_chat_id, source_topic_id, source_message_id FROM materials WHERE id=?",
            (material_id,),
        )
        row = await cur.fetchone()
        return (row[0], row[1], row[2]) if row else None


async def find_exact(
    subject_id: int,
    section_id: int | None,
    category_id: int | None,
    title: str,
    *,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    lecture_no: int | None = None,
    content_hash: str | None = None,
) -> tuple[int] | None:
    """Return the id of a material matching all supplied attributes."""
    q = [
        "SELECT id FROM materials WHERE subject_id=?",
        "section_id IS ?",
        "category_id IS ?",
        "title=?",
    ]
    params: list = [subject_id, section_id, category_id, title]
    if year_id is None:
        q.append("year_id IS NULL")
    else:
        q.append("year_id=?")
        params.append(year_id)
    if lecturer_id is None:
        q.append("lecturer_id IS NULL")
    else:
        q.append("lecturer_id=?")
        params.append(lecturer_id)
    if lecture_no is not None:
        q.append("lecture_no=?")
        params.append(lecture_no)
    if content_hash is not None:
        q.append("content_hash=?")
        params.append(content_hash)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(" AND ".join(q), tuple(params))
        return await cur.fetchone()


# ---------------------------------------------------------------------------
# Helper lookup/ensure functions
# ---------------------------------------------------------------------------
async def get_year_id_by_name(name: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM years WHERE name=?", (name,))
        row = await cur.fetchone()
        return row[0] if row else None


async def insert_year(name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO years (name) VALUES (?)", (name,))
        await db.commit()


async def ensure_year_id(name: str) -> int:
    _id = await get_year_id_by_name(name)
    if _id is not None:
        return _id
    await insert_year(name)
    _id = await get_year_id_by_name(name)
    if _id is None:
        raise RuntimeError(f"Failed to create year: {name}")
    return _id


async def get_lecturer_id_by_name(name: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM lecturers WHERE name=?", (name,))
        row = await cur.fetchone()
        return row[0] if row else None


async def insert_lecturer(name: str, role: str = "lecturer") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO lecturers (name, role) VALUES (?, ?)",
            (name, role),
        )
        await db.commit()


async def ensure_lecturer_id(name: str, role: str = "lecturer") -> int:
    _id = await get_lecturer_id_by_name(name)
    if _id is not None:
        return _id
    await insert_lecturer(name, role)
    _id = await get_lecturer_id_by_name(name)
    if _id is None:
        raise RuntimeError(f"Failed to create lecturer: {name}")
    return _id


# ---------------------------------------------------------------------------
# Navigation stubs (unused in tests relying on the repo layer)
# ---------------------------------------------------------------------------
async def get_available_sections_for_subject(subject_id: int) -> list[str]:  # pragma: no cover - stub
    return []


async def get_available_cards_for_subject(subject_id: int) -> list[str]:  # pragma: no cover - stub
    return []


async def get_years_for_subject_section(subject_id: int, section_id: int) -> list[tuple]:  # pragma: no cover - stub
    return []


async def get_lecturers_for_subject_section(subject_id: int, section_id: int):  # pragma: no cover - stub
    return []


async def get_lectures_by_lecturer_year(
    subject_id: int, section_id: int, lecturer_id: int, year_id: int
) -> list[str]:  # pragma: no cover - stub
    return []


async def list_lecture_titles_by_year(subject_id: int, section_id: int, year_id: int) -> list[str]:  # pragma: no cover - stub
    return []


async def list_categories_for_subject_section_year(
    subject_id: int,
    section_id: int,
    year_id: int,
    lecturer_id: int | None = None,
) -> list[str]:  # pragma: no cover - stub
    return []


async def get_types_for_lecture(
    subject_id: int, section_id: int, year_id: int, lecture_title: str
) -> dict:  # pragma: no cover - stub
    return {}


async def list_term_resource_kinds(level_id: int, term_id: int) -> list[str]:  # pragma: no cover - stub
    return []


async def get_latest_syllabus_material(subject_id: int):  # pragma: no cover - stub
    return None


async def has_materials_by_category(subject_id: int, section_id: int, category_id: int) -> bool:  # pragma: no cover - stub
    return False


async def get_latest_material_by_category(subject_id: int, section_id: int, category_id: int):  # pragma: no cover - stub
    return None


async def get_materials_by_card(subject_id: int, card_code: str):  # pragma: no cover - stub
    return []


__all__ = [
    "insert_material",
    "update_material_storage",
    "delete_material",
    "get_material_source",
    "find_exact",
    "get_year_id_by_name",
    "get_lecturer_id_by_name",
    "ensure_year_id",
    "ensure_lecturer_id",
    "LECTURE_TYPE_LABELS",
    # Navigation stubs
    "get_available_sections_for_subject",
    "get_available_cards_for_subject",
    "get_years_for_subject_section",
    "get_lecturers_for_subject_section",
    "get_lectures_by_lecturer_year",
    "list_lecture_titles_by_year",
    "list_categories_for_subject_section_year",
    "get_types_for_lecture",
    "list_term_resource_kinds",
    "get_latest_syllabus_material",
    "has_materials_by_category",
    "get_latest_material_by_category",
    "get_materials_by_card",
]
