import asyncio

import pytest

from bot.parser.context import parse_context, ContextResult, ParseError
from bot.repo import hashtags, linking

pytestmark = pytest.mark.anyio


async def _setup_hashtags():
    sid_alias = await hashtags.create_alias("physics")
    await hashtags.create_mapping(sid_alias, "subject", 1)
    sec_alias = await hashtags.create_alias("theory")
    await hashtags.create_mapping(sec_alias, "section", 2)


async def test_resolve_from_topic(repo_db):
    gid = await linking.upsert_group(100, "G")
    await linking.upsert_topic(gid, 5, 1, section_id=2)
    ctx, err = await parse_context(gid, 5, [])
    assert err is None
    assert ctx == ContextResult(subject_id=1, section_id=2, source="topic")


async def test_resolve_from_hashtags(repo_db):
    await _setup_hashtags()
    ctx, err = await parse_context(1, None, ["#physics", "#theory"])
    assert err is None
    assert ctx == ContextResult(subject_id=1, section_id=2, source="hashtags")


async def test_missing_context_error(repo_db):
    await _setup_hashtags()
    ctx, err = await parse_context(1, None, ["#physics"])
    assert ctx is None
    assert isinstance(err, ParseError)
    assert err.message == "E-NO-CONTEXT"
