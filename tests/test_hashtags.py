import asyncio
import pytest

from bot.parser.hashtags import parse_hashtags
from bot.repo import hashtags, taxonomy


@pytest.fixture()
def seed(repo_db):
    async def _seed():
        lecture_id = await taxonomy.create_item_type(
            "lecture", "محاضرة", "Lecture", requires_lecture=True
        )
        video_id = await taxonomy.create_item_type(
            "video", "فيديو", "Video", requires_lecture=False
        )
        aid = await hashtags.create_alias("lecture", "lecture")
        await hashtags.create_mapping(aid, "item_type", lecture_id, is_content_tag=True)
        aid = await hashtags.create_alias("video", "video")
        await hashtags.create_mapping(aid, "item_type", video_id, is_content_tag=True)
        await hashtags.create_alias("المحاضرة", "lecture_tag")
    asyncio.run(_seed())
    return repo_db


@pytest.mark.anyio
async def test_parse_hashtags_valid(seed):
    text = "#lecture\n#1446\n#المحاضرة_1: العنوان"
    info, error = await parse_hashtags(text)
    assert error is None
    assert info.content_type == "lecture"
    assert info.year == 1446
    assert info.lecture_no == 1
    assert info.title == "العنوان"


@pytest.mark.anyio
async def test_parse_hashtags_multi_content(seed):
    text = "#lecture\n#video"
    _, error = await parse_hashtags(text)
    assert error == "E-HT-MULTI"


@pytest.mark.anyio
async def test_parse_hashtags_missing_session(seed):
    text = "#lecture\n#1446"
    _, error = await parse_hashtags(text)
    assert error == "E-NO-SESSION"


@pytest.mark.anyio
async def test_parse_hashtags_no_content(seed):
    text = "#1446\n#المحاضرة_1: العنوان"
    _, error = await parse_hashtags(text)
    assert error == "E-NO-CONTEXT"


@pytest.mark.anyio
async def test_parse_hashtags_unknown_alias(seed):
    text = "#lecture\n#مجهول"
    _, error = await parse_hashtags(text)
    assert error == "E-ALIAS-UNKNOWN"
