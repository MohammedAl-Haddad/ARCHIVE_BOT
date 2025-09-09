import asyncio

from bot.parser.caption_parser import ParseError, parse_message
from bot.repo import hashtags


def test_parse_message_resolves_normalized_hashtags(repo_db):
    async def setup() -> None:
        for idx, tag in enumerate(["test1", "physics1", "تجربة"], start=1):
            aid = await hashtags.create_alias(tag)
            await hashtags.create_mapping(aid, "subject", idx)

    asyncio.run(setup())

    text = "انظر إلى #Te‏ST1 و#PHYsics١ و#physics1 و#تجربة‏ #تجربة"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert len(result.hashtags) == 3
    assert all(h["target_kind"] == "subject" for h in result.hashtags)


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
