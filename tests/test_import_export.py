import asyncio

import pytest

from bot.handlers import import_export
from bot.repo import taxonomy, hashtags


def test_export_import_roundtrip(repo_db):
    sid = asyncio.run(taxonomy.create_section("theory", "نظري", "Theory"))
    cid = asyncio.run(
        taxonomy.create_card(
            "slides", "سلايدات", "Slides", section_id=sid, show_when_empty=1
        )
    )
    iid = asyncio.run(
        taxonomy.create_item_type("pdf", "بي دي اف", "PDF", requires_lecture=1)
    )
    alias_id = asyncio.run(hashtags.create_alias("hw", "hw"))
    asyncio.run(hashtags.create_mapping(alias_id, "card", cid))
    asyncio.run(taxonomy.set_subject_section_enable(1, sid, sort_order=1))

    data = asyncio.run(import_export.export_taxonomy())
    report = asyncio.run(import_export.import_taxonomy(data, dry_run=True))
    # nothing to add/update on a fresh import
    for t in data.keys():
        if t == "presets":
            continue
        assert report["add"][t] == []
        assert report["update"][t] == []
        assert report["conflicts"][t] == []


def test_dry_run_and_upsert(repo_db):
    asyncio.run(taxonomy.create_section("theory", "نظري", "Theory"))
    data = {
        "sections": [
            {"key": "theory", "label_ar": "نظري", "label_en": "Theory 2", "is_enabled": 1, "sort_order": 0}
        ]
    }
    report = asyncio.run(import_export.import_taxonomy(data, dry_run=True))
    assert report["update"]["sections"] == ["theory"]
    report = asyncio.run(import_export.import_taxonomy(data, dry_run=True, strict=True))
    assert report["conflicts"]["sections"] == ["theory"]
    # apply update in upsert mode
    report = asyncio.run(import_export.import_taxonomy(data))
    assert report["update"]["sections"] == ["theory"]
    row = asyncio.run(taxonomy.get_section("theory"))
    assert row[3] == "Theory 2"


def test_strict_mode_raises(repo_db):
    asyncio.run(taxonomy.create_section("theory", "نظري", "Theory"))
    data = {
        "sections": [
            {"key": "theory", "label_ar": "نظري", "label_en": "Changed", "is_enabled": 1, "sort_order": 0}
        ]
    }
    with pytest.raises(ValueError):
        asyncio.run(import_export.import_taxonomy(data, strict=True))
