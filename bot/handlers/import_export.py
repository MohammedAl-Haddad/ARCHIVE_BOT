from __future__ import annotations

"""Import/export helpers for dynamic taxonomy tables.

This module supports dumping a subset of taxonomy related tables to a
plain dictionary and restoring them.  Identifiers are purely numeric and
no longer use textual ``key`` fields.  Return reports mimic the original
behaviour used by the tests where each table maps to lists of identifiers
that would be added, updated or conflict.
"""

from typing import Any, Awaitable, Callable

import aiosqlite

from bot.db import base

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
async def export_taxonomy(*, include_presets: bool = False) -> dict[str, Any]:
    """Return a dictionary representing the taxonomy tables."""

    data: dict[str, Any] = {}
    async with aiosqlite.connect(base.DB_PATH) as db:
        # Sections
        cur = await db.execute(
            "SELECT id, label_ar, label_en, is_enabled, sort_order FROM sections ORDER BY id"
        )
        rows = await cur.fetchall()
        data["sections"] = [
            {
                "id": r[0],
                "label_ar": r[1],
                "label_en": r[2],
                "is_enabled": r[3],
                "sort_order": r[4],
            }
            for r in rows
        ]

        # Cards
        cur = await db.execute(
            "SELECT id, section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order FROM cards ORDER BY id"
        )
        rows = await cur.fetchall()
        data["cards"] = [
            {
                "id": r[0],
                "section_id": r[1],
                "label_ar": r[2],
                "label_en": r[3],
                "show_when_empty": r[4],
                "is_enabled": r[5],
                "sort_order": r[6],
            }
            for r in rows
        ]

        # Item types
        cur = await db.execute(
            """
            SELECT id, label_ar, label_en, requires_lecture, allows_year,
                   allows_lecturer, is_enabled, sort_order
            FROM item_types ORDER BY id
            """
        )
        rows = await cur.fetchall()
        data["item_types"] = [
            {
                "id": r[0],
                "label_ar": r[1],
                "label_en": r[2],
                "requires_lecture": r[3],
                "allows_year": r[4],
                "allows_lecturer": r[5],
                "is_enabled": r[6],
                "sort_order": r[7],
            }
            for r in rows
        ]

        # Aliases
        cur = await db.execute(
            "SELECT alias, normalized, lang FROM hashtag_aliases ORDER BY id"
        )
        rows = await cur.fetchall()
        data["aliases"] = [
            {"alias": r[0], "normalized": r[1], "lang": r[2]} for r in rows
        ]

        # Mappings
        cur = await db.execute(
            """
            SELECT a.alias, m.target_kind, m.target_id, m.is_content_tag, m.overrides
            FROM hashtag_mappings m
            JOIN hashtag_aliases a ON a.id = m.alias_id
            ORDER BY m.id
            """
        )
        rows = await cur.fetchall()
        data["mappings"] = [
            {
                "alias": r[0],
                "target_kind": r[1],
                "target_id": r[2],
                "is_content_tag": r[3],
                "overrides": r[4],
            }
            for r in rows
        ]

        # Subject section enable
        cur = await db.execute(
            """
            SELECT subject_id, section_id, is_enabled, sort_order
            FROM subject_section_enable
            ORDER BY subject_id, section_id
            """
        )
        rows = await cur.fetchall()
        data["subject_section_enable"] = [
            {
                "subject_id": r[0],
                "section_id": r[1],
                "is_enabled": r[2],
                "sort_order": r[3],
            }
            for r in rows
        ]

    if include_presets:
        data["presets"] = []
    return data

# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
async def import_taxonomy(
    data: dict[str, Any], *, dry_run: bool = False, strict: bool = False
) -> dict[str, dict[str, list[str]]]:
    """Import *data* produced by :func:`export_taxonomy`."""

    tables = [
        "sections",
        "cards",
        "item_types",
        "aliases",
        "mappings",
        "subject_section_enable",
    ]
    report: dict[str, dict[str, list[str]]] = {
        "add": {t: [] for t in tables},
        "update": {t: [] for t in tables},
        "conflicts": {t: [] for t in tables},
    }

    operations: list[Callable[[], Awaitable[None]]] = []

    async with aiosqlite.connect(base.DB_PATH) as db:
        # Sections
        for sec in data.get("sections", []):
            cur = await db.execute(
                "SELECT label_ar, label_en, is_enabled, sort_order FROM sections WHERE id=?",
                (sec["id"],),
            )
            row = await cur.fetchone()
            incoming = (
                sec.get("label_ar"),
                sec.get("label_en"),
                sec.get("is_enabled", 1),
                sec.get("sort_order", 0),
            )
            ident = str(sec["id"])
            if row is None:
                report["add"]["sections"].append(ident)

                async def _op(sec=sec) -> None:
                    await db.execute(
                        "INSERT INTO sections (id, label_ar, label_en, is_enabled, sort_order) VALUES (?, ?, ?, ?, ?)",
                        (
                            sec["id"],
                            sec.get("label_ar"),
                            sec.get("label_en"),
                            sec.get("is_enabled", 1),
                            sec.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            elif row != incoming:
                if strict:
                    report["conflicts"]["sections"].append(ident)
                else:
                    report["update"]["sections"].append(ident)

                    async def _op(sec=sec) -> None:
                        await db.execute(
                            "UPDATE sections SET label_ar=?, label_en=?, is_enabled=?, sort_order=? WHERE id=?",
                            (
                                sec.get("label_ar"),
                                sec.get("label_en"),
                                sec.get("is_enabled", 1),
                                sec.get("sort_order", 0),
                                sec["id"],
                            ),
                        )

                    operations.append(_op)

        # Cards
        for card in data.get("cards", []):
            cur = await db.execute(
                "SELECT section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order FROM cards WHERE id=?",
                (card["id"],),
            )
            row = await cur.fetchone()
            incoming = (
                card.get("section_id"),
                card.get("label_ar"),
                card.get("label_en"),
                card.get("show_when_empty", 0),
                card.get("is_enabled", 1),
                card.get("sort_order", 0),
            )
            ident = str(card["id"])
            if row is None:
                report["add"]["cards"].append(ident)

                async def _op(card=card) -> None:
                    await db.execute(
                        """INSERT INTO cards (id, section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            card["id"],
                            card.get("section_id"),
                            card.get("label_ar"),
                            card.get("label_en"),
                            card.get("show_when_empty", 0),
                            card.get("is_enabled", 1),
                            card.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            elif row != incoming:
                if strict:
                    report["conflicts"]["cards"].append(ident)
                else:
                    report["update"]["cards"].append(ident)

                    async def _op(card=card) -> None:
                        await db.execute(
                            """UPDATE cards SET section_id=?, label_ar=?, label_en=?, show_when_empty=?, is_enabled=?, sort_order=?
                                   WHERE id=?""",
                            (
                                card.get("section_id"),
                                card.get("label_ar"),
                                card.get("label_en"),
                                card.get("show_when_empty", 0),
                                card.get("is_enabled", 1),
                                card.get("sort_order", 0),
                                card["id"],
                            ),
                        )

                    operations.append(_op)

        # Item types
        for it in data.get("item_types", []):
            cur = await db.execute(
                """
                SELECT label_ar, label_en, requires_lecture, allows_year,
                       allows_lecturer, is_enabled, sort_order
                FROM item_types WHERE id=?
                """,
                (it["id"],),
            )
            row = await cur.fetchone()
            incoming = (
                it.get("label_ar"),
                it.get("label_en"),
                it.get("requires_lecture", 0),
                it.get("allows_year", 1),
                it.get("allows_lecturer", 1),
                it.get("is_enabled", 1),
                it.get("sort_order", 0),
            )
            ident = str(it["id"])
            if row is None:
                report["add"]["item_types"].append(ident)

                async def _op(it=it) -> None:
                    await db.execute(
                        """INSERT INTO item_types (id, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            it["id"],
                            it.get("label_ar"),
                            it.get("label_en"),
                            it.get("requires_lecture", 0),
                            it.get("allows_year", 1),
                            it.get("allows_lecturer", 1),
                            it.get("is_enabled", 1),
                            it.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            elif row != incoming:
                if strict:
                    report["conflicts"]["item_types"].append(ident)
                else:
                    report["update"]["item_types"].append(ident)

                    async def _op(it=it) -> None:
                        await db.execute(
                            """UPDATE item_types
                                   SET label_ar=?, label_en=?, requires_lecture=?, allows_year=?, allows_lecturer=?, is_enabled=?, sort_order=?
                                   WHERE id=?""",
                            (
                                it.get("label_ar"),
                                it.get("label_en"),
                                it.get("requires_lecture", 0),
                                it.get("allows_year", 1),
                                it.get("allows_lecturer", 1),
                                it.get("is_enabled", 1),
                                it.get("sort_order", 0),
                                it["id"],
                            ),
                        )

                    operations.append(_op)

        # Aliases
        for alias in data.get("aliases", []):
            cur = await db.execute(
                "SELECT normalized, lang FROM hashtag_aliases WHERE alias=?",
                (alias["alias"],),
            )
            row = await cur.fetchone()
            incoming = (alias.get("normalized"), alias.get("lang"))
            if row is None:
                report["add"]["aliases"].append(alias["alias"])

                async def _op(alias=alias) -> None:
                    await db.execute(
                        "INSERT INTO hashtag_aliases (alias, normalized, lang) VALUES (?, ?, ?)",
                        (alias["alias"], alias.get("normalized"), alias.get("lang")),
                    )

                operations.append(_op)
            elif row != incoming:
                if strict:
                    report["conflicts"]["aliases"].append(alias["alias"])
                else:
                    report["update"]["aliases"].append(alias["alias"])

                    async def _op(alias=alias) -> None:
                        await db.execute(
                            "UPDATE hashtag_aliases SET normalized=?, lang=? WHERE alias=?",
                            (alias.get("normalized"), alias.get("lang"), alias["alias"]),
                        )

                    operations.append(_op)

        # Mappings
        for m in data.get("mappings", []):
            cur = await db.execute(
                """
                SELECT a.alias, m.target_kind, m.target_id, m.is_content_tag, m.overrides
                FROM hashtag_mappings m JOIN hashtag_aliases a ON a.id = m.alias_id
                WHERE a.alias=?
                """,
                (m["alias"],),
            )
            row = await cur.fetchone()
            incoming = (
                m.get("alias"),
                m.get("target_kind"),
                m.get("target_id"),
                m.get("is_content_tag", 0),
                m.get("overrides"),
            )
            if row is None:
                report["add"]["mappings"].append(m["alias"])

                async def _op(m=m) -> None:
                    cur2 = await db.execute(
                        "SELECT id FROM hashtag_aliases WHERE alias=?", (m.get("alias"),)
                    )
                    arow = await cur2.fetchone()
                    if arow is None:
                        raise ValueError(f"alias {m.get('alias')} missing for mapping")
                    await db.execute(
                        """INSERT INTO hashtag_mappings (alias_id, target_kind, target_id, is_content_tag, overrides)
                               VALUES (?, ?, ?, ?, ?)""",
                        (
                            arow[0],
                            m.get("target_kind"),
                            m.get("target_id"),
                            m.get("is_content_tag", 0),
                            m.get("overrides"),
                        ),
                    )

                operations.append(_op)
            elif row != incoming:
                if strict:
                    report["conflicts"]["mappings"].append(m["alias"])
                else:
                    report["update"]["mappings"].append(m["alias"])

                    async def _op(m=m) -> None:
                        cur2 = await db.execute(
                            "SELECT id FROM hashtag_aliases WHERE alias=?", (m.get("alias"),)
                        )
                        arow = await cur2.fetchone()
                        if arow is None:
                            raise ValueError(f"alias {m.get('alias')} missing for mapping")
                        await db.execute(
                            """UPDATE hashtag_mappings
                                   SET alias_id=?, target_kind=?, target_id=?, is_content_tag=?, overrides=?
                                   WHERE alias_id=?""",
                            (
                                arow[0],
                                m.get("target_kind"),
                                m.get("target_id"),
                                m.get("is_content_tag", 0),
                                m.get("overrides"),
                                arow[0],
                            ),
                        )

                    operations.append(_op)

        # Subject section enable
        for row in data.get("subject_section_enable", []):
            cur = await db.execute(
                "SELECT is_enabled, sort_order FROM subject_section_enable WHERE subject_id=? AND section_id=?",
                (row.get("subject_id"), row.get("section_id")),
            )
            existing = await cur.fetchone()
            incoming = (row.get("is_enabled", 1), row.get("sort_order", 0))
            ident = f"{row.get('subject_id')}:{row.get('section_id')}"
            if existing is None:
                report["add"]["subject_section_enable"].append(ident)

                async def _op(row=row) -> None:
                    await db.execute(
                        """INSERT INTO subject_section_enable (subject_id, section_id, is_enabled, sort_order)
                               VALUES (?, ?, ?, ?)""",
                        (
                            row.get("subject_id"),
                            row.get("section_id"),
                            row.get("is_enabled", 1),
                            row.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            elif existing != incoming:
                if strict:
                    report["conflicts"]["subject_section_enable"].append(ident)
                else:
                    report["update"]["subject_section_enable"].append(ident)

                    async def _op(row=row) -> None:
                        await db.execute(
                            "UPDATE subject_section_enable SET is_enabled=?, sort_order=? WHERE subject_id=? AND section_id=?",
                            (
                                row.get("is_enabled", 1),
                                row.get("sort_order", 0),
                                row.get("subject_id"),
                                row.get("section_id"),
                            ),
                        )

                    operations.append(_op)

    if not dry_run:
        async with aiosqlite.connect(base.DB_PATH) as db:
            for op in operations:
                await op()
            await db.commit()

    return report

