import asyncio
import json

from bot.parser.caption_parser import ParseError, parse_message
from bot.parser import helpers
from bot.repo import hashtags
from bot.repo import taxonomy


def test_parse_message_resolves_normalized_hashtags(repo_db):
    async def setup() -> None:
        tags = [("test1", False), ("physics1", True), ("تجربة", False)]
        for idx, (tag, is_ct) in enumerate(tags, start=1):
            aid = await hashtags.create_alias(tag)
            await hashtags.create_mapping(aid, "subject", idx, is_content_tag=is_ct)

    asyncio.run(setup())

    text = "انظر إلى #Te‏ST1 و#PHYsics١ و#physics1 و#تجربة‏ #تجربة"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert len(result.hashtags) == 3
    assert all(h["target_kind"] == "subject" for h in result.hashtags)
    assert result.content_tag == {
        "target_kind": "subject",
        "target_id": 2,
        "is_content_tag": True,
        "overrides": None,
    }


def test_parse_message_unknown_hashtag(repo_db):
    async def setup() -> None:
        aid = await hashtags.create_alias("known")
        await hashtags.create_mapping(aid, "subject", 1)

    asyncio.run(setup())

    text = "#known #unknown"
    result, error = asyncio.run(parse_message(text))
    assert isinstance(error, ParseError)
    assert error.message == "E-HT-UNKNOWN"
    assert result.hashtags is None
    assert result.content_tag is None


def test_parse_message_no_content_tag_error(repo_db):
    async def setup() -> None:
        aid = await hashtags.create_alias("test")
        await hashtags.create_mapping(aid, "subject", 1)

    asyncio.run(setup())

    result, error = asyncio.run(parse_message("#test"))
    assert isinstance(error, ParseError)
    assert error.message == "E-NO-CONTENT-TAG"
    assert result.content_tag is None
    assert len(result.hashtags) == 1


def test_parse_message_multiple_content_tags_error(repo_db):
    async def setup() -> None:
        for idx, tag in enumerate(["a", "b"], start=1):
            aid = await hashtags.create_alias(tag)
            await hashtags.create_mapping(aid, "subject", idx, is_content_tag=True)

    asyncio.run(setup())

    result, error = asyncio.run(parse_message("#a #b"))
    assert isinstance(error, ParseError)
    assert error.message == "E-HT-MULTI"
    assert result.content_tag is None
    assert len(result.hashtags) == 2


def test_parse_message_extracts_year_and_lecturer_and_logs_raw_tags(repo_db):
    async def setup() -> None:
        aid = await hashtags.create_alias("physics1")
        await hashtags.create_mapping(aid, "subject", 1, is_content_tag=True)

    asyncio.run(setup())

    text = "#physics1 #١٤٤٦ #الدكتور_فلان"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert result.year == 1446
    assert result.lecturer == "فلان"
    assert helpers.raw_tags == ["#physics1", "#١٤٤٦", "#الدكتور_فلان"]
    assert result.raw_tags == helpers.raw_tags


def test_parse_message_extracts_lecture_and_chain(repo_db):
    async def setup() -> None:
        aid = await hashtags.create_alias("physics1")
        await hashtags.create_mapping(aid, "subject", 1, is_content_tag=True)

    asyncio.run(setup())

    text = "#physics1 #المحاضرة_2 //follow"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert result.lecture == 2
    assert result.chain == "follow"
    assert helpers.raw_tags == ["#physics1", "#المحاضرة_2"]
    assert result.raw_tags == helpers.raw_tags


def test_parse_message_resolves_context_from_hashtags(repo_db):
    async def setup() -> None:
        aid_ct = await hashtags.create_alias("ctag")
        await hashtags.create_mapping(aid_ct, "subject", 3, is_content_tag=True)
        aid_sub = await hashtags.create_alias("physics")
        await hashtags.create_mapping(aid_sub, "subject", 1)
        aid_sec = await hashtags.create_alias("theory")
        await hashtags.create_mapping(aid_sec, "section", 2)

    asyncio.run(setup())

    text = "#physics #theory #ctag"
    result, error = asyncio.run(parse_message(text, group_id=1))
    assert error is None
    assert result.subject == 1
    assert result.section == 2


def test_parse_message_respects_overrides(repo_db):
    async def setup() -> None:
        aid = await hashtags.create_alias("physics1")
        ov = json.dumps({"allows_year": False, "allows_lecturer": False})
        await hashtags.create_mapping(
            aid, "subject", 1, is_content_tag=True, overrides=ov
        )

    asyncio.run(setup())

    text = "#physics1 #1446 #الدكتور_فلان"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert result.year is None
    assert result.lecturer is None


def test_parse_message_requires_session_for_item_type(repo_db):
    async def setup() -> None:
        item = await taxonomy.create_item_type("محاضرة", "Lecture", requires_lecture=True)
        aid = await hashtags.create_alias("physics1")
        ov = json.dumps({"item_type": item["id"]})
        await hashtags.create_mapping(
            aid, "subject", 1, is_content_tag=True, overrides=ov
        )

    asyncio.run(setup())

    result, error = asyncio.run(parse_message("#physics1"))
    assert isinstance(error, ParseError)
    assert error.message == "E-NO-SESSION"

    result, error = asyncio.run(parse_message("#physics1 #المحاضرة_1"))
    assert error is None


def test_parse_message_alias_conflict_card_item_type(repo_db):
    async def setup() -> None:
        sec = await taxonomy.create_section("نظري", "Theory")
        card = await taxonomy.create_card("سلايدات", "Slides", section_id=sec["id"])
        item = await taxonomy.create_item_type("ملف", "File")
        aid_content = await hashtags.create_alias("physics1")
        ov = json.dumps({"card": card["id"]})
        await hashtags.create_mapping(
            aid_content, "subject", 1, is_content_tag=True, overrides=ov
        )
        aid_item = await hashtags.create_alias("file")
        await hashtags.create_mapping(aid_item, "item_type", item["id"])

    asyncio.run(setup())

    result, error = asyncio.run(parse_message("#physics1 #file"))
    assert isinstance(error, ParseError)
    assert error.message == "E-ALIAS-CONFLICT"
