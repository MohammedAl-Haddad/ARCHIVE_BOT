from enum import Enum

import aiosqlite
from .base import DB_PATH


class TermResourceKind(str, Enum):
    """Allowed kinds of term resources."""

    ATTENDANCE = "attendance"
    STUDY_PLAN = "study_plan"
    CHANNELS = "channels"
    OUTCOMES = "outcomes"
    TIPS = "tips"
    PROJECTS = "projects"
    PROGRAMS = "programs"
    APPS = "apps"
    FORUMS = "forums"
    SITES = "sites"
    MISC = "misc"


def _validate_kind(kind: str | TermResourceKind) -> str:
    try:
        return TermResourceKind(kind).value
    except ValueError as exc:
        raise ValueError(f"Unsupported term resource kind: {kind}") from exc

async def insert_term_resource(
    level_id: int,
    term_id: int,
    kind: str | TermResourceKind,
    storage_chat_id: int,
    storage_msg_id: int,
):
    kind_val = _validate_kind(kind)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO term_resources (level_id, term_id, kind, tg_storage_chat_id, tg_storage_msg_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (level_id, term_id, kind_val, storage_chat_id, storage_msg_id),
        )
        await db.commit()
        return cur.lastrowid

async def get_latest_term_resource(
    level_id: int, term_id: int, kind: str | TermResourceKind
):
    kind_val = _validate_kind(kind)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT tg_storage_chat_id, tg_storage_msg_id
            FROM term_resources
            WHERE level_id=? AND term_id=? AND kind=?
            ORDER BY id DESC LIMIT 1
            """,
            (level_id, term_id, kind_val),
        )
        return await cur.fetchone()


async def has_term_resource(level_id: int, term_id: int, kind: str | TermResourceKind) -> bool:
    kind_val = _validate_kind(kind)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM term_resources WHERE level_id=? AND term_id=? AND kind=? LIMIT 1",
            (level_id, term_id, kind_val),
        )
        return await cur.fetchone() is not None

async def list_term_resource_kinds(level_id: int, term_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT kind FROM term_resources WHERE level_id=? AND term_id=?",
            (level_id, term_id),
        )
        rows = await cur.fetchall()
        return [row[0] for row in rows]

__all__ = [
    "TermResourceKind",
    "insert_term_resource",
    "get_latest_term_resource",
    "has_term_resource",
    "list_term_resource_kinds",
]
