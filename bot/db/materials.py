import aiosqlite
import re

from .base import DB_PATH

# Arabic labels for lecture material types used in navigation menus
LECTURE_TYPE_LABELS = {
    "lecture": "ملف المحاضرة \U0001F4C4",
    "slides": "السلايدات \U0001F4D1",
    "audio": "الصوت \U0001F50A",
    "board_images": "صور اللوح \U0001F5BC\uFE0F",
    "video": "الفيديو \U0001F3A5",
    "mind_map": "الخريطة الذهنية \U0001F5FA\uFE0F",
    "transcript": "التفريغ \u270D\uFE0F",
    "related": "مواد مرتبطة \U0001F517",
}


def _strip_lecture_prefix(title: str) -> str:
    """Return title without the "محاضرة N:" prefix if present."""
    return title.split(":", 1)[1].strip() if ":" in title else title


async def ensure_file_unique_id_column() -> None:
    """Ensure the ``file_unique_id`` column exists on ``materials`` table."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("PRAGMA table_info(materials)")
        cols = [row[1] for row in await cur.fetchall()]
        if "file_unique_id" not in cols:
            await db.execute("ALTER TABLE materials ADD COLUMN file_unique_id TEXT")
            await db.commit()


# -----------------------------------------------------------------------------
# Helpers for years/lecturers
# -----------------------------------------------------------------------------
async def get_year_id_by_name(name: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM years WHERE name=?", (name,))
        row = await cur.fetchone()
        return row[0] if row else None


async def get_lecturer_id_by_name(name: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM lecturers WHERE name=?", (name,))
        row = await cur.fetchone()
        return row[0] if row else None


async def insert_material(
    subject_id: int,
    section: str,
    category: str,
    title: str,
    url: str | None = None,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    tg_storage_chat_id: int | None = None,
    tg_storage_msg_id: int | None = None,
    file_unique_id: str | None = None,
    source_chat_id: int | None = None,
    source_topic_id: int | None = None,
    source_message_id: int | None = None,
    created_by_admin_id: int | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO materials (
                subject_id, section, category, title, url, year_id, lecturer_id,
                tg_storage_chat_id, tg_storage_msg_id, file_unique_id, source_chat_id,
                source_topic_id, source_message_id, created_by_admin_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject_id,
                section,
                category,
                title,
                url,
                year_id,
                lecturer_id,
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
    file_unique_id: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE materials SET tg_storage_chat_id=?, tg_storage_msg_id=?, file_unique_id=? WHERE id=?",
            (chat_id, msg_id, file_unique_id, material_id),
        )
        await db.commit()


async def get_material_source(
    material_id: int,
) -> tuple[int | None, int | None, int | None] | None:
    """Return source identifiers for *material_id*.

    The tuple contains ``(source_chat_id, source_topic_id, source_message_id)``.
    ``None`` is returned if the material does not exist.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT source_chat_id, source_topic_id, source_message_id
            FROM materials WHERE id=?
            """,
            (material_id,),
        )
        row = await cur.fetchone()
        return (row[0], row[1], row[2]) if row else None


async def delete_material(material_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()


async def insert_year(name: str):
    """Insert a new year record if it does not already exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO years (name) VALUES (?)", (name,))
        await db.commit()


async def insert_lecturer(name: str, role: str = "lecturer"):
    """Insert a lecturer with a *role* if it does not already exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO lecturers (name, role) VALUES (?, ?)",
            (name, role),
        )
        await db.commit()


async def ensure_year_id(name: str) -> int:
    """Return the id for *name*, inserting a new year if necessary."""
    _id = await get_year_id_by_name(name)
    if _id is not None:
        return _id
    await insert_year(name)
    _id = await get_year_id_by_name(name)
    if _id is None:
        raise RuntimeError(f"Failed to create year: {name}")
    return _id


async def ensure_lecturer_id(name: str, role: str = "lecturer") -> int:
    """Return the id for *name*, inserting a new lecturer if needed."""
    _id = await get_lecturer_id_by_name(name)
    if _id is not None:
        return _id
    await insert_lecturer(name, role)
    _id = await get_lecturer_id_by_name(name)
    if _id is None:
        raise RuntimeError(f"Failed to create lecturer: {name}")
    return _id


async def find_exact(
    subject_id: int,
    section: str,
    category: str,
    title: str,
    *,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    alt_title: str | None = None,
) -> tuple[int] | None:
    """Return material id matching all provided attributes exactly.

    ``alt_title`` allows matching legacy records that stored the lecture title
    without the "محاضرة N:" prefix.
    """
    if alt_title and alt_title != title:
        q = (
            "SELECT id FROM materials WHERE subject_id=? AND section=? "
            "AND category=? AND title IN (?, ?)"
        )
        params: list = [subject_id, section, category, title, alt_title]
    else:
        q = (
            "SELECT id FROM materials WHERE subject_id=? AND section=? "
            "AND category=? AND title=?"
        )
        params = [subject_id, section, category, title]
    if year_id is None:
        q += " AND year_id IS NULL"
    else:
        q += " AND year_id=?"
        params.append(year_id)
    if lecturer_id is None:
        q += " AND lecturer_id IS NULL"
    else:
        q += " AND lecturer_id=?"
        params.append(lecturer_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, tuple(params))
        return await cur.fetchone()
# -----------------------------------------------------------------------------
# Filters for years/lecturers/categories
# -----------------------------------------------------------------------------
async def get_years_for_subject_section(subject_id: int, section: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT y.id, y.name
            FROM materials m
            JOIN years y ON y.id = m.year_id
            WHERE m.subject_id = ? AND m.section = ?
              AND (m.url IS NOT NULL OR m.tg_storage_msg_id IS NOT NULL)
            ORDER BY y.name DESC
            """,
            (subject_id, section),
        )
        return await cur.fetchall()


async def get_lecturers_for_subject_section(subject_id: int, section: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT l.id, l.name
            FROM materials m
            JOIN lecturers l ON l.id = m.lecturer_id
            WHERE m.subject_id = ? AND m.section = ?
              AND (m.url IS NOT NULL OR m.tg_storage_msg_id IS NOT NULL)
            ORDER BY l.name
            """,
            (subject_id, section),
        )
        return await cur.fetchall()


async def has_lecture_category(subject_id: int, section: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT 1
            FROM materials
            WHERE subject_id=? AND section=? AND category='lecture'
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            LIMIT 1
            """,
            (subject_id, section),
        )
        return (await cur.fetchone()) is not None


async def list_lecture_titles(subject_id: int, section: str) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT title
            FROM materials
            WHERE subject_id=? AND section=? AND category='lecture'
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY title
            """,
            (subject_id, section),
        )
        return [r[0] for r in await cur.fetchall()]


async def list_lecture_titles_by_year(subject_id: int, section: str, year_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT title
            FROM materials
            WHERE subject_id=? AND section=? AND category='lecture' AND year_id=?
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY title
            """,
            (subject_id, section, year_id),
        )
        return [r[0] for r in await cur.fetchall()]


async def list_lecture_titles_by_lecturer(subject_id: int, section: str, lecturer_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT title
            FROM materials
            WHERE subject_id=? AND section=? AND category='lecture' AND lecturer_id=?
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY title
            """,
            (subject_id, section, lecturer_id),
        )
        return [r[0] for r in await cur.fetchall()]


async def list_lecture_titles_by_lecturer_year(
    subject_id: int, section: str, lecturer_id: int, year_id: int
) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT title
            FROM materials
            WHERE subject_id=? AND section=? AND category='lecture' AND lecturer_id=? AND year_id=?
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY title
            """,
            (subject_id, section, lecturer_id, year_id),
        )
        return [r[0] for r in await cur.fetchall()]


async def get_years_for_subject_section_lecturer(subject_id: int, section: str, lecturer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT y.id, y.name
            FROM materials m
            JOIN years y ON y.id = m.year_id
            WHERE m.subject_id=? AND m.section=? AND m.lecturer_id=?
              AND m.category='lecture' AND m.year_id IS NOT NULL
              AND (m.url IS NOT NULL OR m.tg_storage_msg_id IS NOT NULL)
            ORDER BY y.name DESC
            """,
            (subject_id, section, lecturer_id),
        )
        return await cur.fetchall()
# -----------------------------------------------------------------------------
# Fetch materials
# -----------------------------------------------------------------------------
async def get_lecture_materials(
    subject_id: int,
    section: str,
    *,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    title: str | None = None,
):
    q = """
        SELECT id, title, url, tg_storage_chat_id, tg_storage_msg_id
        FROM materials
        WHERE subject_id=? AND section=? AND category='lecture'
          AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
    """
    params = [subject_id, section]
    if year_id is not None:
        q += " AND year_id=?"
        params.append(year_id)
    if lecturer_id is not None:
        q += " AND lecturer_id=?"
        params.append(lecturer_id)
    if title is not None:
        plain = _strip_lecture_prefix(title)
        if plain and plain != title:
            q += " AND title IN (?, ?)"
            params.extend([title, plain])
        else:
            q += " AND title=?"
            params.append(title)
    q += " ORDER BY id"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, tuple(params))
        return await cur.fetchall()


async def get_materials_by_category(
    subject_id: int,
    section: str,
    category: str,
    *,
    year_id: int | None = None,
    lecturer_id: int | None = None,
    title: str | None = None,
    alt_title: str | None = None,
):
    q = """
        SELECT id, title, url, tg_storage_chat_id, tg_storage_msg_id
        FROM materials
        WHERE subject_id=? AND section=? AND category=?
          AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
    """
    params = [subject_id, section, category]
    if year_id is not None:
        q += " AND year_id=?"
        params.append(year_id)
    if lecturer_id is not None:
        q += " AND lecturer_id=?"
        params.append(lecturer_id)
    if title is not None:
        if alt_title and alt_title != title:
            q += " AND title IN (?, ?)"
            params.extend([title, alt_title])
        else:
            q += " AND title=?"
            params.append(title)
    q += " ORDER BY id"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, tuple(params))
        return await cur.fetchall()


async def has_materials_by_category(subject_id: int, section: str, category: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT 1
            FROM materials
            WHERE subject_id=? AND section=? AND category=?
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            LIMIT 1
            """,
            (subject_id, section, category),
        )
        return (await cur.fetchone()) is not None


async def get_latest_material_by_category(
    subject_id: int, section: str, category: str
):
    """Return latest material for given category or None.

    The returned tuple is ``(tg_storage_chat_id, tg_storage_msg_id, url)``.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT tg_storage_chat_id, tg_storage_msg_id, url
            FROM materials
            WHERE subject_id=? AND section=? AND category=?
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY id DESC
            LIMIT 1
            """,
            (subject_id, section, category),
        )
        return await cur.fetchone()


async def get_latest_syllabus_material(subject_id: int):
    """Return latest syllabus material for a subject or None.

    The returned tuple is ``(tg_storage_chat_id, tg_storage_msg_id, url)``.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT tg_storage_chat_id, tg_storage_msg_id, url
            FROM materials
            WHERE subject_id=? AND category='syllabus'
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
            ORDER BY id DESC
            LIMIT 1
            """,
            (subject_id,),
        )
        return await cur.fetchone()


async def list_categories_for_subject_section_year(
    subject_id: int,
    section: str,
    year_id: int,
    lecturer_id: int | None = None,
) -> list[str]:
    lecture_attachment_cats = (
        "slides",
        "audio",
        "board_images",
        "video",
        "mind_map",
        "transcript",
        "related",
    )

    placeholders = ",".join("?" * len(lecture_attachment_cats))
    q = f"""
        SELECT DISTINCT category
        FROM materials
        WHERE subject_id=? AND section=? AND year_id=? AND category IS NOT NULL
          AND category <> 'lecture'
          AND category NOT IN ({placeholders})
          AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
    """
    params = [subject_id, section, year_id, *lecture_attachment_cats]

    if lecturer_id is not None:
        q += " AND lecturer_id=?"
        params.append(lecturer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, tuple(params))
        return [r[0] for r in await cur.fetchall()]


async def list_categories_for_lecture(
    subject_id: int,
    section: str,
    title: str,
    year_id: int | None = None,
    lecturer_id: int | None = None,
) -> list[str]:
    plain = _strip_lecture_prefix(title)
    if plain != title:
        q = """
            SELECT DISTINCT category
            FROM materials
            WHERE subject_id=? AND section=? AND title IN (?, ?) AND category IS NOT NULL
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
        """
        params = [subject_id, section, title, plain]
    else:
        q = """
            SELECT DISTINCT category
            FROM materials
            WHERE subject_id=? AND section=? AND title=? AND category IS NOT NULL
              AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
        """
        params = [subject_id, section, title]
    if year_id is not None:
        q += " AND year_id=?"
        params.append(year_id)
    if lecturer_id is not None:
        q += " AND lecturer_id=?"
        params.append(lecturer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, tuple(params))
        return [r[0] for r in await cur.fetchall()]


# -----------------------------------------------------------------------------
# Simplified access helpers for navigation
# -----------------------------------------------------------------------------

async def get_years(subject_id: int, section: str) -> list[int]:
    """Return available Hijri years for *subject* and *section*."""
    rows = await get_years_for_subject_section(subject_id, section)
    return [int(name) for _id, name in rows]


def _titles_to_lectures(titles: list[str]) -> list[dict]:
    """Convert raw *titles* to structured lecture info."""
    lectures: list[dict] = []
    for t in titles:
        m = re.search(r"(\d+)", t)
        no = int(m.group(1)) if m else len(lectures) + 1
        title = t.split(":", 1)[1].strip() if ":" in t else t
        lectures.append({"lecture_no": no, "title": title, "raw": t})
    return lectures


async def get_lectures(subject_id: int, section: str) -> list[dict]:
    """Return all lectures for *subject* and *section*."""
    titles = await list_lecture_titles(subject_id, section)
    return _titles_to_lectures(titles)


async def get_lectures_for_lecturer(
    subject_id: int, section: str, lecturer_id: int
) -> list[dict]:
    """Return lectures for a specific *lecturer_id* with numbers extracted."""
    titles = await list_lecture_titles_by_lecturer(subject_id, section, lecturer_id)
    return _titles_to_lectures(titles)


# Backwards compatibility alias
get_lectures_by_lecturer = get_lectures_for_lecturer


async def get_lectures_by_lecturer_year(
    subject_id: int, section: str, lecturer_id: int, year_id: int
) -> list[dict]:
    """Return lectures for a given lecturer and year."""
    titles = await list_lecture_titles_by_lecturer_year(
        subject_id, section, lecturer_id, year_id
    )
    return _titles_to_lectures(titles)


async def get_lectures_by_year(subject_id: int, section: str, year_id: int) -> list[dict]:
    """Return lectures within a specific *year_id* with extracted numbers."""
    titles = await list_lecture_titles_by_year(subject_id, section, year_id)
    return _titles_to_lectures(titles)


async def get_types_for_lecture(
    subject_id: int,
    section: str,
    year_id: int,
    lecture_title: str,
) -> dict[str, tuple[int, str | None, int | None, int | None]]:
    """Return available types for a lecture mapped to material records."""
    plain = _strip_lecture_prefix(lecture_title)
    cats = await list_categories_for_lecture(
        subject_id, section, lecture_title, year_id=year_id
    )
    result: dict[str, tuple[int, str | None, int | None, int | None]] = {}
    for cat in cats:
        mats = await get_materials_by_category(
            subject_id,
            section,
            cat,
            year_id=year_id,
            title=lecture_title,
            alt_title=plain if plain != lecture_title else None,
        )
        if mats:
            _id, title, url, chat_id, msg_id = mats[0]
            result[cat] = (_id, url, chat_id, msg_id)
    return result


async def get_year_specials(subject_id: int, section: str, year_id: int) -> dict:
    """Return flags for booklet and exam models in a year."""
    booklet = bool(
        await get_materials_by_category(subject_id, section, "booklet", year_id=year_id)
    )
    exam_mid = bool(
        await get_materials_by_category(subject_id, section, "exam_mid", year_id=year_id)
    )
    exam_final = bool(
        await get_materials_by_category(subject_id, section, "exam_final", year_id=year_id)
    )
    return {
        "has_booklet": booklet,
        "has_exam_mid": exam_mid,
        "has_exam_final": exam_final,
    }
