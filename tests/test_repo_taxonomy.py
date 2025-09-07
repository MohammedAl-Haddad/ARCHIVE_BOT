import asyncio

from bot.repo import taxonomy


def test_section_crud(repo_db):
    sid = asyncio.run(taxonomy.create_section("theory", "نظري", "Theory"))
    row = asyncio.run(taxonomy.get_section("theory"))
    assert row[0] == sid
    asyncio.run(taxonomy.update_section(sid, label_en="Theory Updated"))
    row = asyncio.run(taxonomy.get_section("theory"))
    assert row[3] == "Theory Updated"
    asyncio.run(taxonomy.delete_section(sid))
    assert asyncio.run(taxonomy.get_section("theory")) is None


def test_card_crud(repo_db):
    section_id = asyncio.run(taxonomy.create_section("lab", "عملي", "Lab"))
    cid = asyncio.run(taxonomy.create_card("slides", "سلايدات", "Slides", section_id=section_id))
    row = asyncio.run(taxonomy.get_card("slides"))
    assert row[0] == cid
    asyncio.run(taxonomy.update_card(cid, label_en="Slides Updated"))
    row = asyncio.run(taxonomy.get_card("slides"))
    assert row[3] == "Slides Updated"
    asyncio.run(taxonomy.delete_card(cid))
    assert asyncio.run(taxonomy.get_card("slides")) is None


def test_item_type_crud(repo_db):
    iid = asyncio.run(taxonomy.create_item_type("pdf", "بي دي اف", "PDF", requires_lecture=True))
    row = asyncio.run(taxonomy.get_item_type("pdf"))
    assert row[0] == iid
    asyncio.run(taxonomy.update_item_type(iid, label_en="PDF Updated"))
    row = asyncio.run(taxonomy.get_item_type("pdf"))
    assert row[3] == "PDF Updated"
    asyncio.run(taxonomy.delete_item_type(iid))
    assert asyncio.run(taxonomy.get_item_type("pdf")) is None


def test_subject_section_enable(repo_db):
    sid = asyncio.run(taxonomy.create_section("disc", "نقاش", "Discussion"))
    asyncio.run(taxonomy.set_subject_section_enable(1, sid, sort_order=2))
    rows = asyncio.run(taxonomy.get_enabled_sections_for_subject(1))
    assert rows == [(sid, 1, 2)]
