import asyncio

from bot.repo import taxonomy


def _run(coro):
    return asyncio.run(coro)


def test_crud_and_language(repo_db):
    # Sections
    sec1 = _run(taxonomy.create_section("نظري", "Theory", sort_order=2))
    sec2 = _run(
        taxonomy.create_section("عملي", "Lab", sort_order=1, is_enabled=False)
    )

    assert _run(taxonomy.get_section(sec1["id"], lang="en"))["label"] == "Theory"
    _run(taxonomy.update_section(sec1["id"], label_en="Theory Updated"))
    assert (
        _run(taxonomy.get_section(sec1["id"], lang="en"))["label"]
        == "Theory Updated"
    )
    assert _run(taxonomy.get_section(sec2["id"])) is None

    sections = _run(taxonomy.get_sections())
    assert [s["id"] for s in sections] == [sec1["id"]]
    sections_all = _run(taxonomy.get_sections(lang="en", include_disabled=True))
    assert [s["id"] for s in sections_all] == [sec2["id"], sec1["id"]]
    assert sections_all[0]["label"] == "Lab"

    # Cards
    card1 = _run(
        taxonomy.create_card("سلايدات", "Slides", section_id=sec1["id"], sort_order=1)
    )
    card2 = _run(
        taxonomy.create_card(
            "مراجع", "References", section_id=sec1["id"], sort_order=0, is_enabled=False
        )
    )
    assert _run(taxonomy.get_card(card1["id"], lang="en"))["label"] == "Slides"
    _run(taxonomy.update_card(card1["id"], label_en="Slides Updated"))
    assert (
        _run(taxonomy.get_card(card1["id"], lang="en"))["label"]
        == "Slides Updated"
    )
    cards = _run(taxonomy.get_cards(section_id=sec1["id"]))
    assert [c["id"] for c in cards] == [card1["id"]]
    cards_all = _run(
        taxonomy.get_cards(section_id=sec1["id"], include_disabled=True, lang="en")
    )
    assert [c["id"] for c in cards_all] == [card2["id"], card1["id"]]
    assert cards_all[0]["label"] == "References"
    _run(taxonomy.delete_card(card1["id"]))
    assert _run(taxonomy.get_card(card1["id"])) is None

    # Item types
    it1 = _run(taxonomy.create_item_type("بي دي اف", "PDF", sort_order=1))
    it2 = _run(
        taxonomy.create_item_type("صورة", "Image", sort_order=0, is_enabled=False)
    )
    assert _run(taxonomy.get_item_type(it1["id"], lang="en"))["label"] == "PDF"
    _run(taxonomy.update_item_type(it1["id"], label_en="PDF Updated"))
    assert (
        _run(taxonomy.get_item_type(it1["id"], lang="en"))["label"]
        == "PDF Updated"
    )
    item_types = _run(taxonomy.get_item_types())
    assert [i["id"] for i in item_types] == [it1["id"]]
    item_types_all = _run(taxonomy.get_item_types(include_disabled=True, lang="en"))
    assert [i["id"] for i in item_types_all] == [it2["id"], it1["id"]]
    assert item_types_all[0]["label"] == "Image"
    _run(taxonomy.delete_item_type(it1["id"]))
    assert _run(taxonomy.get_item_type(it1["id"])) is None


def test_section_item_types_and_subject_sections(repo_db):
    sec = _run(taxonomy.create_section("نظري", "Theory"))
    it1 = _run(taxonomy.create_item_type("بي دي اف", "PDF", sort_order=1))
    it2 = _run(taxonomy.create_item_type("صورة", "Image", sort_order=0))

    _run(taxonomy.set_section_item_type(sec["id"], it1["id"], sort_order=1))
    _run(
        taxonomy.set_section_item_type(
            sec["id"], it2["id"], sort_order=0, is_enabled=False
        )
    )
    items = _run(taxonomy.get_item_types_for_section(sec["id"]))
    assert [i["id"] for i in items] == [it1["id"]]
    items_all = _run(
        taxonomy.get_item_types_for_section(sec["id"], include_disabled=True, lang="en")
    )
    assert [i["id"] for i in items_all] == [it2["id"], it1["id"]]
    assert items_all[0]["label"] == "Image"

    sec2 = _run(taxonomy.create_section("مختبر", "Lab", sort_order=1))
    _run(taxonomy.set_subject_section_enable(1, sec["id"], sort_order=2))
    _run(
        taxonomy.set_subject_section_enable(
            1, sec2["id"], sort_order=1, is_enabled=False
        )
    )
    enabled = _run(taxonomy.get_sections_for_subject(1))
    assert [s["id"] for s in enabled] == [sec["id"]]
    enabled_all = _run(
        taxonomy.get_sections_for_subject(1, include_disabled=True, lang="en")
    )
    assert [s["id"] for s in enabled_all] == [sec2["id"], sec["id"]]
    assert enabled_all[0]["label"] == "Lab"
