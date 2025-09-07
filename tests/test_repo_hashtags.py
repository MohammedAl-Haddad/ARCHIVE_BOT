import asyncio

from bot.repo import hashtags


def test_alias_crud(repo_db):
    aid = asyncio.run(hashtags.create_alias("math", "math"))
    row = asyncio.run(hashtags.get_alias("math"))
    assert row[0] == aid
    asyncio.run(hashtags.update_alias(aid, normalized="maths"))
    row = asyncio.run(hashtags.get_alias("math"))
    assert row[2] == "maths"
    asyncio.run(hashtags.delete_alias(aid))
    assert asyncio.run(hashtags.get_alias("math")) is None


def test_mapping_and_lookup(repo_db):
    aid = asyncio.run(hashtags.create_alias("physics", "physics"))
    mid = asyncio.run(hashtags.create_mapping(aid, "subject", 5))
    rows = asyncio.run(hashtags.get_mappings_for_alias("physics"))
    assert rows[0][0] == mid
    targets = asyncio.run(hashtags.lookup_targets("physics"))
    assert targets == [("subject", 5)]
