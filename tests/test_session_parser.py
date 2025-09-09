import asyncio
import pytest

from bot.parser.session import parse_session, SessionInfo, ParseError
from bot.repo import taxonomy

pytestmark = pytest.mark.anyio


async def test_parse_session_extracts_number_and_title(repo_db):
    item = await taxonomy.create_item_type("محاضرة", "Lecture", requires_lecture=True)
    info, err = await parse_session(item["id"], "#المحاضرة_5: المقدمة")
    assert err is None
    assert info == SessionInfo(number=5, title="المقدمة", entity_label="محاضرة")


async def test_parse_session_missing_number_error(repo_db):
    item = await taxonomy.create_item_type("محاضرة", "Lecture", requires_lecture=True)
    info, err = await parse_session(item["id"], "#المحاضرة: المقدمة")
    assert isinstance(err, ParseError)
    assert err.message == "E-NO-SESSION"
    assert info.entity_label == "محاضرة"
