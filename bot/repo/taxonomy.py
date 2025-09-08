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
    lang: str = "ar",
) -> dict:
    """Insert a new section and return it as a dictionary.

    The returned dict contains at least ``id``, ``label``, ``sort_order`` and
    ``is_enabled`` with ``label`` chosen based on *lang*.
    """

    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO sections (label_ar, label_en, is_enabled, sort_order) VALUES (?, ?, ?, ?)",
            (label_ar, label_en, int(is_enabled), sort_order),
        )
        await db.commit()
        section_id = cur.lastrowid

    return await get_section(section_id, lang=lang, include_disabled=True)


@translate_errors
async def get_section(
    section_id: int,
    *,
    lang: str = "ar",
    include_disabled: bool = False,
) -> dict | None:
    """Return a single section as a dictionary or ``None``.

    By default only enabled sections are returned unless ``include_disabled`` is
    set.
    """

    async with connect() as db:
        query = (
            f"SELECT id, label_{lang}, sort_order, is_enabled FROM sections"
            " WHERE id=?"
        )
        params = [section_id]
        if not include_disabled:
            query += " AND is_enabled=1"
        cur = await db.execute(query, params)
        row = await cur.fetchone()

    if row is None:
        return None
    return {
        "id": row[0],
        "label": row[1],
        "sort_order": row[2],
        "is_enabled": bool(row[3]),
    }


@translate_errors
async def update_section(
    section_id: int,
    *,
    lang: str = "ar",
    **fields,
) -> dict | None:
    """Update a section and return the updated row as a dictionary."""

    if not fields:
        return await get_section(section_id, lang=lang, include_disabled=True)
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [section_id]
    async with connect() as db:
        await db.execute(f"UPDATE sections SET {cols} WHERE id=?", params)
        await db.commit()
    return await get_section(section_id, lang=lang, include_disabled=True)


@translate_errors
async def delete_section(section_id: int) -> None:
    """Delete a section by id."""

    async with connect() as db:
        await db.execute("DELETE FROM sections WHERE id=?", (section_id,))
        await db.commit()


@translate_errors
async def get_sections(
    *, lang: str = "ar", include_disabled: bool = False
) -> list[dict]:
    """Return all sections ordered by ``sort_order``.

    Only enabled sections are returned unless ``include_disabled`` is ``True``.
    """

    async with connect() as db:
        query = f"SELECT id, label_{lang}, sort_order, is_enabled FROM sections"
        if not include_disabled:
            query += " WHERE is_enabled=1"
        query += " ORDER BY sort_order"
        cur = await db.execute(query)
        rows = await cur.fetchall()

    return [
        {"id": r[0], "label": r[1], "sort_order": r[2], "is_enabled": bool(r[3])}
        for r in rows
    ]

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
    lang: str = "ar",
) -> dict:
    """Insert a new card and return it as a dictionary."""

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
        card_id = cur.lastrowid

    return await get_card(card_id, lang=lang, include_disabled=True)


@translate_errors
async def get_card(
    card_id: int,
    *,
    lang: str = "ar",
    include_disabled: bool = False,
) -> dict | None:
    """Return a card as a dictionary or ``None``."""

    async with connect() as db:
        query = (
            f"SELECT id, section_id, label_{lang}, show_when_empty, is_enabled, sort_order"
            " FROM cards WHERE id=?"
        )
        params = [card_id]
        if not include_disabled:
            query += " AND is_enabled=1"
        cur = await db.execute(query, params)
        row = await cur.fetchone()

    if row is None:
        return None
    return {
        "id": row[0],
        "section_id": row[1],
        "label": row[2],
        "show_when_empty": bool(row[3]),
        "is_enabled": bool(row[4]),
        "sort_order": row[5],
    }


@translate_errors
async def update_card(
    card_id: int,
    *,
    lang: str = "ar",
    **fields,
) -> dict | None:
    """Update a card and return the updated row as a dictionary."""

    if not fields:
        return await get_card(card_id, lang=lang, include_disabled=True)
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [card_id]
    async with connect() as db:
        await db.execute(f"UPDATE cards SET {cols} WHERE id=?", params)
        await db.commit()
    return await get_card(card_id, lang=lang, include_disabled=True)


@translate_errors
async def delete_card(card_id: int) -> None:
    """Delete a card by id."""

    async with connect() as db:
        await db.execute("DELETE FROM cards WHERE id=?", (card_id,))
        await db.commit()


@translate_errors
async def get_cards(
    *, section_id: int | None = None, lang: str = "ar", include_disabled: bool = False
) -> list[dict]:
    """Return cards optionally filtered by section."""

    async with connect() as db:
        query = f"SELECT id, section_id, label_{lang}, show_when_empty, is_enabled, sort_order FROM cards"
        clauses = []
        params: list = []
        if section_id is not None:
            clauses.append("section_id=?")
            params.append(section_id)
        if not include_disabled:
            clauses.append("is_enabled=1")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY sort_order"
        cur = await db.execute(query, params)
        rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "section_id": r[1],
            "label": r[2],
            "show_when_empty": bool(r[3]),
            "is_enabled": bool(r[4]),
            "sort_order": r[5],
        }
        for r in rows
    ]

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
    lang: str = "ar",
) -> dict:
    """Insert an item type and return it as a dictionary."""

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
        item_type_id = cur.lastrowid

    return await get_item_type(item_type_id, lang=lang, include_disabled=True)


@translate_errors
async def get_item_type(
    item_type_id: int,
    *,
    lang: str = "ar",
    include_disabled: bool = False,
) -> dict | None:
    """Return an item type as a dictionary or ``None``."""

    async with connect() as db:
        query = (
            f"SELECT id, label_{lang}, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order"
            " FROM item_types WHERE id=?"
        )
        params = [item_type_id]
        if not include_disabled:
            query += " AND is_enabled=1"
        cur = await db.execute(query, params)
        row = await cur.fetchone()

    if row is None:
        return None
    return {
        "id": row[0],
        "label": row[1],
        "requires_lecture": bool(row[2]),
        "allows_year": bool(row[3]),
        "allows_lecturer": bool(row[4]),
        "is_enabled": bool(row[5]),
        "sort_order": row[6],
    }


@translate_errors
async def update_item_type(
    item_type_id: int,
    *,
    lang: str = "ar",
    **fields,
) -> dict | None:
    """Update an item type and return the updated row as a dictionary."""

    if not fields:
        return await get_item_type(item_type_id, lang=lang, include_disabled=True)
    cols = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [item_type_id]
    async with connect() as db:
        await db.execute(f"UPDATE item_types SET {cols} WHERE id=?", params)
        await db.commit()
    return await get_item_type(item_type_id, lang=lang, include_disabled=True)


@translate_errors
async def delete_item_type(item_type_id: int) -> None:
    """Delete an item type by id."""

    async with connect() as db:
        await db.execute("DELETE FROM item_types WHERE id=?", (item_type_id,))
        await db.commit()


@translate_errors
async def get_item_types(
    *, lang: str = "ar", include_disabled: bool = False
) -> list[dict]:
    """Return all item types ordered by ``sort_order``."""

    async with connect() as db:
        query = (
            f"SELECT id, label_{lang}, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order"
            " FROM item_types"
        )
        if not include_disabled:
            query += " WHERE is_enabled=1"
        query += " ORDER BY sort_order"
        cur = await db.execute(query)
        rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "label": r[1],
            "requires_lecture": bool(r[2]),
            "allows_year": bool(r[3]),
            "allows_lecturer": bool(r[4]),
            "is_enabled": bool(r[5]),
            "sort_order": r[6],
        }
        for r in rows
    ]

# ---------------------------------------------------------------------------
# Section item types
# ---------------------------------------------------------------------------


@translate_errors
async def set_section_item_type(
    section_id: int,
    item_type_id: int,
    *,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> None:
    """Upsert a section-item_type mapping."""

    async with connect() as db:
        await db.execute(
            """INSERT INTO section_item_types
                (section_id, item_type_id, is_enabled, sort_order)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(section_id, item_type_id)
                DO UPDATE SET is_enabled=excluded.is_enabled, sort_order=excluded.sort_order""",
            (section_id, item_type_id, int(is_enabled), sort_order),
        )
        await db.commit()


@translate_errors
async def get_item_types_for_section(
    section_id: int,
    *,
    lang: str = "ar",
    include_disabled: bool = False,
) -> list[dict]:
    """Return item types linked to a section."""

    async with connect() as db:
        query = f"""SELECT it.id, it.label_{lang}, sit.sort_order, sit.is_enabled
                    FROM section_item_types AS sit
                    JOIN item_types AS it ON it.id = sit.item_type_id
                    WHERE sit.section_id=?"""
        params = [section_id]
        if not include_disabled:
            query += " AND sit.is_enabled=1 AND it.is_enabled=1"
        query += " ORDER BY sit.sort_order"
        cur = await db.execute(query, params)
        rows = await cur.fetchall()

    return [
        {"id": r[0], "label": r[1], "sort_order": r[2], "is_enabled": bool(r[3])}
        for r in rows
    ]

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
async def get_sections_for_subject(
    subject_id: int,
    *,
    lang: str = "ar",
    include_disabled: bool = False,
) -> list[dict]:
    """Return sections enabled for a subject."""

    async with connect() as db:
        query = f"""SELECT s.id, s.label_{lang}, sse.sort_order, sse.is_enabled
                    FROM subject_section_enable AS sse
                    JOIN sections AS s ON s.id = sse.section_id
                    WHERE sse.subject_id=?"""
        params = [subject_id]
        if not include_disabled:
            query += " AND sse.is_enabled=1 AND s.is_enabled=1"
        query += " ORDER BY sse.sort_order"
        cur = await db.execute(query, params)
        rows = await cur.fetchall()

    return [
        {"id": r[0], "label": r[1], "sort_order": r[2], "is_enabled": bool(r[3])}
        for r in rows
    ]
