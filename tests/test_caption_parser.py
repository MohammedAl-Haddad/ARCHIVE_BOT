import asyncio

from bot.parser.caption_parser import parse_message


def test_parse_message_extracts_normalized_hashtags():
    text = "انظر إلى #Te‏ST1 و#PHYsics١ و#physics1 و#تجربة‏ #تجربة"
    result, error = asyncio.run(parse_message(text))
    assert error is None
    assert result.hashtags == ["test1", "physics1", "تجربة"]
