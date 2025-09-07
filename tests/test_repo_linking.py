import asyncio

from bot.repo import linking


def test_group_crud(repo_db):
    gid = asyncio.run(linking.upsert_group(123, "Group"))
    row = asyncio.run(linking.get_group(123))
    assert row[0] == gid
    asyncio.run(linking.upsert_group(123, "Group2", level_id=1))
    row = asyncio.run(linking.get_group(123))
    assert row[3] == 1


def test_topic_crud(repo_db):
    gid = asyncio.run(linking.upsert_group(456, "G"))
    tid = asyncio.run(linking.upsert_topic(gid, 789, 3, section_id=2))
    row = asyncio.run(linking.get_topic(gid, 789))
    assert row[0] == tid
    asyncio.run(linking.upsert_topic(gid, 789, 4, section_id=1))
    row = asyncio.run(linking.get_topic(gid, 789))
    assert row[3] == 4 and row[4] == 1
