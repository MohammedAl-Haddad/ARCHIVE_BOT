import json
import pytest

from bot.parser import helpers
from bot.parser.caption_parser import ParseError, parse_message
from bot.repo import hashtags, linking, taxonomy


pytestmark = pytest.mark.anyio


@pytest.fixture
async def create_alias(repo_db):
    async def _create(tag, kind, ident, *, is_content=False, overrides=None):
        aid = await hashtags.create_alias(tag)
        await hashtags.create_mapping(
            aid,
            kind,
            ident,
            is_content_tag=is_content,
            overrides=overrides,
        )
        return aid

    return _create


@pytest.fixture
async def create_topic(repo_db):
    async def _create(subject_id=1, section_id=2):
        gid = await linking.upsert_group(100, "G")
        await linking.upsert_topic(gid, 5, subject_id, section_id=section_id)
        return gid, 5

    return _create


async def test_topic_success(repo_db, create_alias, create_topic):
    await create_alias("ctag", "subject", 1, is_content=True)
    gid, tid = await create_topic()
    result, err = await parse_message("#ctag", group_id=gid, tg_topic_id=tid)
    assert err is None
    assert result.subject == 1
    assert result.section == 2


async def test_unknown_alias(repo_db, create_alias):
    await create_alias("known", "subject", 1)
    result, err = await parse_message("#known #unknown")
    assert isinstance(err, ParseError)
    assert err.message == "E-HT-UNKNOWN"
    assert result.hashtags is None


async def test_no_content_tag_error(repo_db, create_alias):
    await create_alias("tag", "subject", 1)
    result, err = await parse_message("#tag")
    assert isinstance(err, ParseError)
    assert err.message == "E-NO-CONTENT-TAG"
    assert result.content_tag is None
    assert len(result.hashtags) == 1


async def test_multiple_content_tags_error(repo_db, create_alias):
    await create_alias("a", "subject", 1, is_content=True)
    await create_alias("b", "subject", 2, is_content=True)
    result, err = await parse_message("#a #b")
    assert isinstance(err, ParseError)
    assert err.message == "E-HT-MULTI"
    assert result.content_tag is None
    assert len(result.hashtags) == 2


async def test_extracts_year_and_lecturer(repo_db, create_alias):
    await create_alias("physics1", "subject", 1, is_content=True)
    text = "#physics1 #١٤٤٦ #الدكتور_فلان"
    result, err = await parse_message(text)
    assert err is None
    assert result.year == 1446
    assert result.lecturer == "فلان"
    assert helpers.raw_tags == ["#physics1", "#١٤٤٦", "#الدكتور_فلان"]
    assert result.raw_tags == helpers.raw_tags


async def test_extracts_lecture_and_chain(repo_db, create_alias):
    await create_alias("physics1", "subject", 1, is_content=True)
    text = "#physics1 #المحاضرة_2 //follow"
    result, err = await parse_message(text)
    assert err is None
    assert result.lecture == 2
    assert result.chain == "follow"
    assert helpers.raw_tags == ["#physics1", "#المحاضرة_2"]
    assert result.raw_tags == helpers.raw_tags


async def test_context_from_hashtags(repo_db, create_alias):
    await create_alias("ctag", "subject", 3, is_content=True)
    await create_alias("physics", "subject", 1)
    await create_alias("theory", "section", 2)
    result, err = await parse_message("#physics #theory #ctag", group_id=1)
    assert err is None
    assert result.subject == 1
    assert result.section == 2


async def test_respects_overrides(repo_db, create_alias):
    ov = json.dumps({"allows_year": False, "allows_lecturer": False})
    await create_alias("physics1", "subject", 1, is_content=True, overrides=ov)
    text = "#physics1 #1446 #الدكتور_فلان"
    result, err = await parse_message(text)
    assert err is None
    assert result.year is None
    assert result.lecturer is None


async def test_alias_conflict(repo_db, create_alias):
    sec = await taxonomy.create_section("نظري", "Theory")
    card = await taxonomy.create_card("سلايدات", "Slides", section_id=sec["id"])
    item = await taxonomy.create_item_type("ملف", "File")
    ov = json.dumps({"card": card["id"]})
    await create_alias("physics1", "subject", 1, is_content=True, overrides=ov)
    await create_alias("file", "item_type", item["id"])
    result, err = await parse_message("#physics1 #file")
    assert isinstance(err, ParseError)
    assert err.message == "E-ALIAS-CONFLICT"


