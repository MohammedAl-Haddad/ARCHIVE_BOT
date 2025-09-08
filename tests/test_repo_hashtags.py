import asyncio
import pytest

from bot.repo import hashtags
from bot.repo import RepoConflict


def test_alias_crud(repo_db):
    aid = asyncio.run(hashtags.create_alias("math"))
    row = asyncio.run(hashtags.get_alias("math"))
    assert row[0] == aid
    asyncio.run(hashtags.update_alias(aid, normalized="maths"))
    row = asyncio.run(hashtags.get_alias("math"))
    assert row[2] == "maths"
    asyncio.run(hashtags.delete_alias(aid))
    assert asyncio.run(hashtags.get_alias("math")) is None


def test_normalization_unique_and_lookup(repo_db):
    aid = asyncio.run(hashtags.create_alias(" PHYsics١ "))
    row = asyncio.run(hashtags.get_alias(" PHYsics١ "))
    assert row[2] == "physics1"

    assert asyncio.run(hashtags.is_known_alias("physics1"))
    assert asyncio.run(hashtags.get_alias_id("physics١")) == aid

    mid = asyncio.run(hashtags.create_mapping(aid, "subject", 5, is_content_tag=True))
    rows = asyncio.run(hashtags.get_mappings_for_alias("physics1"))
    assert rows[0][0] == mid
    targets = asyncio.run(hashtags.lookup_targets("  physics١  "))
    assert targets == [("subject", 5)]
    resolved = asyncio.run(hashtags.resolve_content_tag("physics1"))
    assert resolved == {
        "target_kind": "subject",
        "target_id": 5,
        "is_content_tag": True,
        "overrides": None,
    }

    with pytest.raises(RepoConflict):
        asyncio.run(hashtags.create_alias("physics 1"))

    aid2 = asyncio.run(hashtags.create_alias("chem"))
    with pytest.raises(RepoConflict):
        asyncio.run(hashtags.create_mapping(aid2, "subject", 5))
