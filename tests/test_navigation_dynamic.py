import asyncio
import pytest

from bot.repo import taxonomy, materials, connect


def _run(coro):
    return asyncio.run(coro)


async def _has_material_for_card(subject_id: int, card_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute(
            """SELECT 1 FROM materials
                   WHERE subject_id=? AND category_id=?
                     AND (url IS NOT NULL OR tg_storage_msg_id IS NOT NULL)
                   LIMIT 1""",
            (subject_id, card_id),
        )
        return await cur.fetchone() is not None


async def build_subject_menu(subject_id: int) -> dict:
    sections = []
    enabled_sections = await taxonomy.get_sections_for_subject(subject_id)
    for sec in enabled_sections:
        if await materials.count_by_section(subject_id, sec["id"]) > 0:
            sections.append(sec)
    enabled_ids = {s["id"] for s in enabled_sections}
    cards = []
    for sec_id in enabled_ids:
        for card in await taxonomy.get_cards(section_id=sec_id):
            if card["show_when_empty"] or await _has_material_for_card(subject_id, card["id"]):
                cards.append(card)
    return {"sections": sections, "cards": cards}


def test_section_shown_when_material_exists(repo_db):
    it = _run(taxonomy.create_item_type("ملف", "File"))["id"]
    sec = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    _run(taxonomy.set_section_item_type(sec, it))
    _run(taxonomy.set_subject_section_enable(1, sec))
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec,
            category_id=None,
            item_type_id=it,
            title="A",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    menu = _run(build_subject_menu(1))
    assert [s["id"] for s in menu["sections"]] == [sec]


def test_section_hidden_without_material(repo_db):
    it = _run(taxonomy.create_item_type("ملف", "File"))["id"]
    sec = _run(taxonomy.create_section("عملي", "Lab"))["id"]
    _run(taxonomy.set_section_item_type(sec, it))
    _run(taxonomy.set_subject_section_enable(1, sec))
    menu = _run(build_subject_menu(1))
    assert menu["sections"] == []


def test_section_hidden_when_disabled(repo_db):
    it = _run(taxonomy.create_item_type("ملف", "File"))["id"]
    sec = _run(taxonomy.create_section("نظري2", "Theory2"))["id"]
    _run(taxonomy.set_section_item_type(sec, it))
    _run(taxonomy.set_subject_section_enable(1, sec, is_enabled=False))
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec,
            category_id=None,
            item_type_id=it,
            title="B",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    menu = _run(build_subject_menu(1))
    assert menu["sections"] == []


def test_card_shown_with_material(repo_db):
    sec = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    _run(taxonomy.set_subject_section_enable(1, sec))
    card = _run(taxonomy.create_card("سلايدات", "Slides", section_id=sec))["id"]
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec,
            category_id=card,
            item_type_id=None,
            title="Slide1",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    menu = _run(build_subject_menu(1))
    assert [c["id"] for c in menu["cards"]] == [card]


def test_card_hidden_without_material(repo_db):
    sec = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    _run(taxonomy.set_subject_section_enable(1, sec))
    _run(taxonomy.create_card("سلايدات", "Slides", section_id=sec))
    menu = _run(build_subject_menu(1))
    assert menu["cards"] == []


def test_card_show_when_empty_true(repo_db):
    sec = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    _run(taxonomy.set_subject_section_enable(1, sec))
    card = _run(
        taxonomy.create_card(
            "تنبيه", "Info", section_id=sec, show_when_empty=True
        )
    )["id"]
    menu = _run(build_subject_menu(1))
    assert card in [c["id"] for c in menu["cards"]]


def test_card_hidden_when_section_disabled(repo_db):
    sec = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    _run(taxonomy.set_subject_section_enable(1, sec, is_enabled=False))
    card = _run(taxonomy.create_card("سلايدات", "Slides", section_id=sec))["id"]
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec,
            category_id=card,
            item_type_id=None,
            title="Slide",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    menu = _run(build_subject_menu(1))
    assert card not in [c["id"] for c in menu["cards"]]


def test_menu_empty_when_no_content(repo_db):
    menu = _run(build_subject_menu(1))
    assert menu == {"sections": [], "cards": []}


def test_multiple_sections_sorted(repo_db):
    it = _run(taxonomy.create_item_type("ملف", "File"))["id"]
    sec1 = _run(taxonomy.create_section("نظري", "Theory", sort_order=2))["id"]
    sec2 = _run(taxonomy.create_section("عملي", "Lab", sort_order=1))["id"]
    _run(taxonomy.set_section_item_type(sec1, it))
    _run(taxonomy.set_section_item_type(sec2, it))
    _run(taxonomy.set_subject_section_enable(1, sec1, sort_order=2))
    _run(taxonomy.set_subject_section_enable(1, sec2, sort_order=1))
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec1,
            category_id=None,
            item_type_id=it,
            title="A",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec2,
            category_id=None,
            item_type_id=it,
            title="B",
            tg_storage_chat_id=1,
            tg_storage_msg_id=2,
        )
    )
    menu = _run(build_subject_menu(1))
    assert [s["id"] for s in menu["sections"]] == [sec2, sec1]


def test_card_hidden_if_section_not_enabled(repo_db):
    sec_enabled = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    sec_hidden = _run(taxonomy.create_section("مختبر", "Lab"))["id"]
    _run(taxonomy.set_subject_section_enable(1, sec_enabled))
    card = _run(taxonomy.create_card("سلايدات", "Slides", section_id=sec_hidden))["id"]
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sec_hidden,
            category_id=card,
            item_type_id=None,
            title="Slide",
            tg_storage_chat_id=1,
            tg_storage_msg_id=1,
        )
    )
    menu = _run(build_subject_menu(1))
    assert card not in [c["id"] for c in menu["cards"]]
