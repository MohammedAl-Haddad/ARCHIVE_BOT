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
            "SELECT id, label_ar, label_en, is_enabled, sort_order, created_at, updated_at FROM sections ORDER BY id"
        )
        rows = await cur.fetchall()
        data["sections"] = [
            {
                "id": r[0],
                "label_ar": r[1],
                "label_en": r[2],
                "is_enabled": r[3],
                "sort_order": r[4],
                "created_at": r[5],
                "updated_at": r[6],
            }
            for r in rows
        ]

        # Cards
        cur = await db.execute(
            "SELECT id, section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order, created_at, updated_at FROM cards ORDER BY id"
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
                "created_at": r[7],
                "updated_at": r[8],
            }
            for r in rows
        ]

        # Item types
        cur = await db.execute(
            "SELECT id, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order, created_at, updated_at FROM item_types ORDER BY id"
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
                "created_at": r[8],
                "updated_at": r[9],
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

        # Subject section enable
        cur = await db.execute(
            "SELECT subject_id, section_id, is_enabled, sort_order, created_at, updated_at FROM subject_section_enable ORDER BY subject_id, section_id"
        )
        rows = await cur.fetchall()
        data["subject_section_enable"] = [
            {
                "subject_id": r[0],
                "section_id": r[1],
                "is_enabled": r[2],
                "sort_order": r[3],
                "created_at": r[4],
                "updated_at": r[5],
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
            sid = sec["id"]
            cur = await db.execute(
                "SELECT label_ar, label_en, is_enabled, sort_order FROM sections WHERE id=?",
                (sid,),
            )
            row = await cur.fetchone()
            incoming = (
                sec.get("label_ar"),
                sec.get("label_en"),
                sec.get("is_enabled", 1),
                sec.get("sort_order", 0),
            )
            if row is None:
                report["add"]["sections"].append(sid)

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
            else:
                existing = row
                if existing != incoming:
                    if strict:
                        report["conflicts"]["sections"].append(sid)
                    else:
                        report["update"]["sections"].append(sid)

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

        # Cards --------------------------------------------------------------------
        for card in data.get("cards", []):
            cid = card["id"]
            cur = await db.execute(
                "SELECT label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order FROM cards WHERE id=?",
                (cid,),
            )
            row = await cur.fetchone()
            incoming = (
                card.get("label_ar"),
                card.get("label_en"),
                card.get("section_id"),
                card.get("show_when_empty", 0),
                card.get("is_enabled", 1),
                card.get("sort_order", 0),
            )
            if row is None:
                report["add"]["cards"].append(cid)

                async def _op(card=card) -> None:
                    await db.execute(
                        """INSERT INTO cards
                            (id, section_id, label_ar, label_en, show_when_empty, is_enabled, sort_order)
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
            else:
                existing = row
                if existing != incoming:
                    if strict:
                        report["conflicts"]["cards"].append(cid)
                    else:
                        report["update"]["cards"].append(cid)

                        async def _op(card=card) -> None:
                            await db.execute(
                                """UPDATE cards SET section_id=?, label_ar=?, label_en=?, show_when_empty=?,
                                       is_enabled=?, sort_order=? WHERE id=?""",
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

        # Item types ----------------------------------------------------------------
        for item in data.get("item_types", []):
            iid = item["id"]
            cur = await db.execute(
                """SELECT label_ar, label_en, requires_lecture, allows_year,
                       allows_lecturer, is_enabled, sort_order FROM item_types WHERE id=?""",
                (iid,),
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
                report["add"]["item_types"].append(iid)

                async def _op(item=item) -> None:
                    await db.execute(
                        """INSERT INTO item_types
                            (id, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item["id"],
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
                        report["conflicts"]["item_types"].append(iid)
                    else:
                        report["update"]["item_types"].append(iid)

                        async def _op(item=item) -> None:
                            await db.execute(
                                """UPDATE item_types SET label_ar=?, label_en=?, requires_lecture=?,
                                       allows_year=?, allows_lecturer=?, is_enabled=?, sort_order=? WHERE id=?""",
                                (
                                    item.get("label_ar"),
                                    item.get("label_en"),
                                    item.get("requires_lecture", 0),
                                    item.get("allows_year", 1),
                                    item.get("allows_lecturer", 1),
                                    item.get("is_enabled", 1),
                                    item.get("sort_order", 0),
                                    item["id"],
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
            cur = await db.execute(
                "SELECT is_enabled, sort_order FROM subject_section_enable WHERE subject_id=? AND section_id=?",
                (row["subject_id"], row["section_id"]),
            )
            existing = await cur.fetchone()
            incoming = (
                row.get("is_enabled", 1),
                row.get("sort_order", 0),
            )
            ident = f"{row['subject_id']}:{row['section_id']}"
            if existing is None:
                report["add"]["subject_section_enable"].append(ident)

                async def _op(row=row) -> None:
                    await db.execute(
                        """INSERT INTO subject_section_enable
                            (subject_id, section_id, is_enabled, sort_order)
                            VALUES (?, ?, ?, ?)""",
                        (
                            row["subject_id"],
                            row.get("section_id"),
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

                        async def _op(row=row) -> None:
                            await db.execute(
                                """UPDATE subject_section_enable SET is_enabled=?, sort_order=?
                                       WHERE subject_id=? AND section_id=?""",
                                (
                                    row.get("is_enabled", 1),
                                    row.get("sort_order", 0),
                                    row["subject_id"],
                                    row.get("section_id"),
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
