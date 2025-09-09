import asyncio

from bot.parser.caption_parser import ParseError, parse_message
from bot.repo import hashtags


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
