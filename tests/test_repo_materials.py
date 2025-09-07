import asyncio

from bot.repo import materials, taxonomy


def test_materials_crud(repo_db):
    sid = asyncio.run(taxonomy.create_section("theory", "نظري", "Theory"))
    cid = asyncio.run(taxonomy.create_card("lecture", "محاضرة", "Lecture", section_id=sid))
    iid = asyncio.run(taxonomy.create_item_type("file", "ملف", "File"))
    mid = asyncio.run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=cid,
            item_type_id=iid,
            title="Intro",
            content_hash="abc",
        )
    )
    row = asyncio.run(materials.get_material(mid))
    assert row[0] == mid
    asyncio.run(materials.update_material_storage(mid, 10, 20, file_unique_id="x"))
    row = asyncio.run(materials.get_material(mid))
    assert row[11] == 10 and row[12] == 20 and row[13] == "x"
    found = asyncio.run(materials.find_by_hash("abc"))
    assert found[0] == mid
    asyncio.run(materials.delete_material(mid))
    assert asyncio.run(materials.get_material(mid)) is None
