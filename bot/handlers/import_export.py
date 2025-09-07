from __future__ import annotations

"""Import/export helpers for dynamic taxonomy tables.

The module provides two main asynchronous helpers:

``export_taxonomy``
    Dump the taxonomy-related tables into a JSON compatible ``dict``.

``import_taxonomy``
    Load a previously exported dictionary back into the database.  The
    function supports ``dry_run`` mode which only reports the operations
    without touching the database and a ``strict`` mode which raises an
    error when conflicts are detected instead of updating existing rows.

Both helpers operate only on a subset of tables (sections, cards,
item types, hashtag aliases and mappings, subject_section_enable) and
are designed to be idempotent – running the import multiple times with
the same data will not create duplicates.
"""

from typing import Any, Awaitable, Callable

import aiosqlite

from bot.db import base

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
async def export_taxonomy(*, include_presets: bool = False) -> dict[str, Any]:
    """Return a dictionary representing the taxonomy tables.

    The keys appear in the order required by the JSON schema:
    ``sections`` → ``cards`` → ``item_types`` → ``aliases`` →
    ``mappings`` → ``subject_section_enable`` (→ ``presets``).
    """

    data: dict[str, Any] = {}
    async with aiosqlite.connect(base.DB_PATH) as db:
        # Sections
        cur = await db.execute(
            "SELECT key, label_ar, label_en, is_enabled, sort_order FROM sections ORDER BY id"
        )
        rows = await cur.fetchall()
        data["sections"] = [
            {
                "key": r[0],
                "label_ar": r[1],
                "label_en": r[2],
                "is_enabled": r[3],
                "sort_order": r[4],
            }
            for r in rows
        ]

        # Cards – join with sections to export section key
        cur = await db.execute(
            """
            SELECT c.key, c.label_ar, c.label_en, s.key, c.show_when_empty,
                   c.is_enabled, c.sort_order
            FROM cards c LEFT JOIN sections s ON c.section_id = s.id
            ORDER BY c.id
            """
        )
        rows = await cur.fetchall()
        data["cards"] = [
            {
                "key": r[0],
                "label_ar": r[1],
                "label_en": r[2],
                "section": r[3],
                "show_when_empty": r[4],
                "is_enabled": r[5],
                "sort_order": r[6],
            }
            for r in rows
        ]

        # Item types
        cur = await db.execute(
            """
            SELECT key, label_ar, label_en, requires_lecture, allows_year,
                   allows_lecturer, is_enabled, sort_order
            FROM item_types ORDER BY id
            """
        )
        rows = await cur.fetchall()
        data["item_types"] = [
            {
                "key": r[0],
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
            {
                "alias": r[0],
                "normalized": r[1],
                "lang": r[2],
            }
            for r in rows
        ]

        # Mappings – joined with alias string
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

        # Subject section enable – export using section key
        cur = await db.execute(
            """
            SELECT e.subject_id, s.key, e.is_enabled, e.sort_order
            FROM subject_section_enable e
            JOIN sections s ON s.id = e.section_id
            ORDER BY e.subject_id, s.key
            """
        )
        rows = await cur.fetchall()
        data["subject_section_enable"] = [
            {
                "subject_id": r[0],
                "section": r[1],
                "is_enabled": r[2],
                "sort_order": r[3],
            }
            for r in rows
        ]

    if include_presets:
        data["presets"] = []  # Placeholder for future extensions
    return data

# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
async def import_taxonomy(
    data: dict[str, Any], *, dry_run: bool = False, strict: bool = False
) -> dict[str, dict[str, list[str]]]:
    """Import *data* produced by :func:`export_taxonomy`.

    Parameters
    ----------
    data:
        Dictionary following the schema documented in ``docs/IMPORT_SCHEMA.md``.
    dry_run:
        When ``True`` the database is left untouched and only a report of
        the required operations is returned.
    strict:
        When ``True`` any would-be update is reported as a conflict and, if
        ``dry_run`` is ``False``, a :class:`ValueError` is raised.
    """

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
        # Sections -----------------------------------------------------------------
        for sec in data.get("sections", []):
            cur = await db.execute(
                "SELECT label_ar, label_en, is_enabled, sort_order FROM sections WHERE key=?",
                (sec["key"],),
            )
            row = await cur.fetchone()
            incoming = (
                sec.get("label_ar"),
                sec.get("label_en"),
                sec.get("is_enabled", 1),
                sec.get("sort_order", 0),
            )
            if row is None:
                report["add"]["sections"].append(sec["key"])

                async def _op(sec=sec) -> None:
                    await db.execute(
                        "INSERT INTO sections (key, label_ar, label_en, is_enabled, sort_order) VALUES (?, ?, ?, ?, ?)",
                        (
                            sec["key"],
                            sec.get("label_ar"),
                            sec.get("label_en"),
                            sec.get("is_enabled", 1),
                            sec.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            else:
                existing = row
                if existing != incoming:
                    if strict:
                        report["conflicts"]["sections"].append(sec["key"])
                    else:
                        report["update"]["sections"].append(sec["key"])

                        async def _op(sec=sec) -> None:
                            await db.execute(
                                "UPDATE sections SET label_ar=?, label_en=?, is_enabled=?, sort_order=? WHERE key=?",
                                (
                                    sec.get("label_ar"),
                                    sec.get("label_en"),
                                    sec.get("is_enabled", 1),
                                    sec.get("sort_order", 0),
                                    sec["key"],
                                ),
                            )

                        operations.append(_op)

        # Cards --------------------------------------------------------------------
        for card in data.get("cards", []):
            cur = await db.execute(
                """
                SELECT c.label_ar, c.label_en, s.key, c.show_when_empty,
                       c.is_enabled, c.sort_order
                FROM cards c LEFT JOIN sections s ON c.section_id = s.id
                WHERE c.key=?
                """,
                (card["key"],),
            )
            row = await cur.fetchone()
            incoming = (
                card.get("label_ar"),
                card.get("label_en"),
                card.get("section"),
                card.get("show_when_empty", 0),
                card.get("is_enabled", 1),
                card.get("sort_order", 0),
            )
            # resolve section id for operations
            section_key = card.get("section")
            section_id = None
            if section_key is not None:
                cur = await db.execute("SELECT id FROM sections WHERE key=?", (section_key,))
                sec_row = await cur.fetchone()
                section_id = sec_row[0] if sec_row else None
            if row is None:
                report["add"]["cards"].append(card["key"])

                async def _op(card=card, section_id=section_id) -> None:
                    await db.execute(
                        """INSERT INTO cards
                            (key, label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            card["key"],
                            card.get("label_ar"),
                            card.get("label_en"),
                            section_id,
                            card.get("show_when_empty", 0),
                            card.get("is_enabled", 1),
                            card.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            else:
                existing = row
                if existing != incoming:
                    if strict:
                        report["conflicts"]["cards"].append(card["key"])
                    else:
                        report["update"]["cards"].append(card["key"])

                        async def _op(card=card, section_id=section_id) -> None:
                            await db.execute(
                                """UPDATE cards SET label_ar=?, label_en=?, section_id=?, show_when_empty=?,
                                       is_enabled=?, sort_order=? WHERE key=?""",
                                (
                                    card.get("label_ar"),
                                    card.get("label_en"),
                                    section_id,
                                    card.get("show_when_empty", 0),
                                    card.get("is_enabled", 1),
                                    card.get("sort_order", 0),
                                    card["key"],
                                ),
                            )

                        operations.append(_op)

        # Item types ----------------------------------------------------------------
        for item in data.get("item_types", []):
            cur = await db.execute(
                """
                SELECT label_ar, label_en, requires_lecture, allows_year,
                       allows_lecturer, is_enabled, sort_order
                FROM item_types WHERE key=?
                """,
                (item["key"],),
            )
            row = await cur.fetchone()
            incoming = (
                item.get("label_ar"),
                item.get("label_en"),
                item.get("requires_lecture", 0),
                item.get("allows_year", 1),
                item.get("allows_lecturer", 1),
                item.get("is_enabled", 1),
                item.get("sort_order", 0),
            )
            if row is None:
                report["add"]["item_types"].append(item["key"])

                async def _op(item=item) -> None:
                    await db.execute(
                        """INSERT INTO item_types
                            (key, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item["key"],
                            item.get("label_ar"),
                            item.get("label_en"),
                            item.get("requires_lecture", 0),
                            item.get("allows_year", 1),
                            item.get("allows_lecturer", 1),
                            item.get("is_enabled", 1),
                            item.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            else:
                existing = row
                if existing != incoming:
                    if strict:
                        report["conflicts"]["item_types"].append(item["key"])
                    else:
                        report["update"]["item_types"].append(item["key"])

                        async def _op(item=item) -> None:
                            await db.execute(
                                """UPDATE item_types SET label_ar=?, label_en=?, requires_lecture=?,
                                       allows_year=?, allows_lecturer=?, is_enabled=?, sort_order=? WHERE key=?""",
                                (
                                    item.get("label_ar"),
                                    item.get("label_en"),
                                    item.get("requires_lecture", 0),
                                    item.get("allows_year", 1),
                                    item.get("allows_lecturer", 1),
                                    item.get("is_enabled", 1),
                                    item.get("sort_order", 0),
                                    item["key"],
                                ),
                            )

                        operations.append(_op)

        # Aliases -------------------------------------------------------------------
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
            else:
                if row != incoming:
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

        # Mappings ------------------------------------------------------------------
        for mapping in data.get("mappings", []):
            # resolve alias id
            cur = await db.execute(
                "SELECT id FROM hashtag_aliases WHERE alias=?",
                (mapping["alias"],),
            )
            alias_row = await cur.fetchone()
            alias_id = alias_row[0] if alias_row else None
            cur = await db.execute(
                """SELECT is_content_tag, overrides FROM hashtag_mappings
                    WHERE alias_id=? AND target_kind=? AND target_id=?""",
                (alias_id, mapping["target_kind"], mapping["target_id"]),
            )
            row = await cur.fetchone()
            incoming = (
                mapping.get("is_content_tag", 0),
                mapping.get("overrides"),
            )
            ident = f"{mapping['alias']}→{mapping['target_kind']}:{mapping['target_id']}"
            if row is None:
                report["add"]["mappings"].append(ident)

                async def _op(mapping=mapping, alias_id=alias_id) -> None:
                    await db.execute(
                        """INSERT INTO hashtag_mappings (alias_id, target_kind, target_id, is_content_tag, overrides)
                            VALUES (?, ?, ?, ?, ?)""",
                        (
                            alias_id,
                            mapping["target_kind"],
                            mapping["target_id"],
                            mapping.get("is_content_tag", 0),
                            mapping.get("overrides"),
                        ),
                    )

                operations.append(_op)
            else:
                if row != incoming:
                    if strict:
                        report["conflicts"]["mappings"].append(ident)
                    else:
                        report["update"]["mappings"].append(ident)

                        async def _op(mapping=mapping, alias_id=alias_id) -> None:
                            await db.execute(
                                """UPDATE hashtag_mappings SET is_content_tag=?, overrides=?
                                       WHERE alias_id=? AND target_kind=? AND target_id=?""",
                                (
                                    mapping.get("is_content_tag", 0),
                                    mapping.get("overrides"),
                                    alias_id,
                                    mapping["target_kind"],
                                    mapping["target_id"],
                                ),
                            )

                        operations.append(_op)

        # Subject section enable ----------------------------------------------------
        for row in data.get("subject_section_enable", []):
            section_key = row["section"]
            cur = await db.execute("SELECT id FROM sections WHERE key=?", (section_key,))
            sec_row = await cur.fetchone()
            section_id = sec_row[0] if sec_row else None
            cur = await db.execute(
                """SELECT is_enabled, sort_order FROM subject_section_enable
                    WHERE subject_id=? AND section_id=?""",
                (row["subject_id"], section_id),
            )
            existing = await cur.fetchone()
            incoming = (
                row.get("is_enabled", 1),
                row.get("sort_order", 0),
            )
            ident = f"{row['subject_id']}:{section_key}"
            if existing is None:
                report["add"]["subject_section_enable"].append(ident)

                async def _op(row=row, section_id=section_id) -> None:
                    await db.execute(
                        """INSERT INTO subject_section_enable
                            (subject_id, section_id, is_enabled, sort_order)
                            VALUES (?, ?, ?, ?)""",
                        (
                            row["subject_id"],
                            section_id,
                            row.get("is_enabled", 1),
                            row.get("sort_order", 0),
                        ),
                    )

                operations.append(_op)
            else:
                if existing != incoming:
                    if strict:
                        report["conflicts"]["subject_section_enable"].append(ident)
                    else:
                        report["update"]["subject_section_enable"].append(ident)

                        async def _op(row=row, section_id=section_id) -> None:
                            await db.execute(
                                """UPDATE subject_section_enable SET is_enabled=?, sort_order=?
                                       WHERE subject_id=? AND section_id=?""",
                                (
                                    row.get("is_enabled", 1),
                                    row.get("sort_order", 0),
                                    row["subject_id"],
                                    section_id,
                                ),
                            )

                        operations.append(_op)

        # Finalisation -------------------------------------------------------------
        if report["conflicts"] and any(report["conflicts"].values()) and strict:
            if dry_run:
                return report
            raise ValueError("Conflicts encountered in strict mode")

        if not dry_run:
            for op in operations:
                await op()
            await db.commit()

    return report
