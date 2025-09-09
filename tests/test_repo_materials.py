import asyncio
import pytest

from bot.repo import materials, taxonomy, RepoConstraintError


def _run(coro):
    return asyncio.run(coro)


def test_insert_validation(repo_db):
    sid = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    cid = _run(taxonomy.create_card("محاضرة", "Lecture", section_id=sid))["id"]
    iid = _run(taxonomy.create_item_type("ملف", "File"))["id"]

    # both provided
    with pytest.raises(RepoConstraintError):
        _run(
            materials.insert_material(
                subject_id=1,
                section_id=sid,
                category_id=cid,
                item_type_id=iid,
                title="bad",
            )
        )

    # neither provided
    with pytest.raises(RepoConstraintError):
        _run(
            materials.insert_material(
                subject_id=1,
                section_id=sid,
                category_id=None,
                item_type_id=None,
                title="bad",
            )
        )

    # valid insert using item_type
    mid = _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid,
            title="ok",
            content_hash="abc",
        )
    )
    assert isinstance(mid, int)


def test_crud_and_hash(repo_db):
    sid = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    iid = _run(taxonomy.create_item_type("ملف", "File"))["id"]

    mid = _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid,
            title="Intro",
            content_hash="abc",
        )
    )
    row = _run(materials.get_material(mid))
    assert row["id"] == mid

    # update storage info using generic update
    row = _run(
        materials.update_material(
            mid,
            tg_storage_chat_id=10,
            tg_storage_msg_id=20,
            file_unique_id="x",
        )
    )
    assert row["tg_storage_chat_id"] == 10
    assert row["tg_storage_msg_id"] == 20
    assert row["file_unique_id"] == "x"

    found = _run(materials.find_by_hash("abc"))
    assert found and found["id"] == mid

    deleted = _run(materials.delete_material(mid))
    assert deleted["id"] == mid
    assert _run(materials.get_material(mid)) is None


def test_count_queries(repo_db):
    sid = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    iid1 = _run(taxonomy.create_item_type("ملف", "File"))["id"]
    iid2 = _run(taxonomy.create_item_type("رابط", "Link"))["id"]

    _run(taxonomy.set_section_item_type(sid, iid1))
    _run(taxonomy.set_section_item_type(sid, iid2))
    _run(taxonomy.set_subject_section_enable(1, sid))

    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid1,
            title="A",
        )
    )
    _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid2,
            title="B",
        )
    )

    assert _run(materials.count_by_subject(1)) == 2
    assert _run(materials.count_by_section(1, sid)) == 2
    assert _run(materials.count_by_item_type(1, sid, iid1)) == 1

    # disabling the section hides counts unless include_disabled=True
    _run(taxonomy.set_subject_section_enable(1, sid, is_enabled=False))
    assert _run(materials.count_by_subject(1)) == 0
    assert _run(materials.count_by_subject(1, include_disabled=True)) == 2
    assert _run(materials.count_by_section(1, sid)) == 0
    assert _run(materials.count_by_section(1, sid, include_disabled=True)) == 2
    assert _run(materials.count_by_item_type(1, sid, iid1)) == 0
    assert (
        _run(materials.count_by_item_type(1, sid, iid1, include_disabled=True))
        == 1
    )


def test_get_materials_filters_and_enable(repo_db):
    sid = _run(taxonomy.create_section("نظري", "Theory"))["id"]
    iid = _run(taxonomy.create_item_type("ملف", "File"))["id"]

    _run(taxonomy.set_section_item_type(sid, iid))
    _run(taxonomy.set_subject_section_enable(1, sid))

    mid1 = _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid,
            title="Y1L1",
            year_id=1,
            lecturer_id=1,
            lecture_no=1,
        )
    )
    mid2 = _run(
        materials.insert_material(
            subject_id=1,
            section_id=sid,
            category_id=None,
            item_type_id=iid,
            title="Y2L2",
            year_id=2,
            lecturer_id=2,
            lecture_no=2,
        )
    )

    # filter by year
    res = _run(materials.get_materials(1, section_id=sid, year_id=1))
    assert [r["id"] for r in res] == [mid1]

    # filter by lecture number
    res = _run(materials.get_materials(1, section_id=sid, lecture_no=2))
    assert [r["id"] for r in res] == [mid2]

    # disable section for subject
    _run(taxonomy.set_subject_section_enable(1, sid, is_enabled=False))
    res = _run(materials.get_materials(1, section_id=sid))
    assert res == []
    res = _run(materials.get_materials(1, section_id=sid, include_disabled=True))
    assert {r["id"] for r in res} == {mid1, mid2}
