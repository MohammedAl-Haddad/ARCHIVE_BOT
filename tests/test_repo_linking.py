import asyncio

import pytest

from bot.repo import linking, RepoNotFound


def test_group_crud(repo_db):
    gid = asyncio.run(linking.upsert_group(123, "Group"))
    row = asyncio.run(linking.get_group(123))
    assert row[0] == gid
    asyncio.run(linking.upsert_group(123, "Group2", level_id=1))
    row = asyncio.run(linking.get_group(123))
    assert row[3] == 1


def test_topic_crud(repo_db):
    gid = asyncio.run(linking.upsert_group(456, "G"))
    asyncio.run(linking.upsert_topic(gid, 1, 3, section_id=2))
    asyncio.run(linking.upsert_topic(gid, 2, 4, section_id=1))

    binding = asyncio.run(linking.get_binding_by_topic(gid, 2))
    assert binding == {"subject_id": 4, "section_id": 1}

    rows = asyncio.run(linking.get_group_topics(gid))
    assert {r[2] for r in rows} == {1, 2}

    asyncio.run(linking.upsert_topic(gid, 2, 5, section_id=None))
    binding = asyncio.run(linking.get_binding_by_topic(gid, 2))
    assert binding == {"subject_id": 5, "section_id": None}

    asyncio.run(linking.delete_topic(gid, 1))
    rows = asyncio.run(linking.get_group_topics(gid))
    assert [r[2] for r in rows] == [2]
    with pytest.raises(RepoNotFound):
        asyncio.run(linking.get_binding_by_topic(gid, 1))
