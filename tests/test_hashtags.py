import pytest

from bot.parser.hashtags import parse_hashtags
from tests.helpers import TERM_RESOURCE_TAGS


def test_parse_hashtags_accepts_full_lecture_sequence():
    text = "\n".join(
        [
            "#lecture",
            "#المحاضرة_1: العنوان",
            "#1446",
            "#الدكتور_فلان",
        ]
    )
    info, error = parse_hashtags(text)
    assert error is None
    assert info.content_type == "lecture"
    assert info.lecture_no == 1
    assert info.title == "العنوان"
    assert info.year == 1446
    assert info.lecturer == "فلان"


@pytest.mark.parametrize("kind, tags", TERM_RESOURCE_TAGS.items())
def test_parse_hashtags_term_resources(kind, tags):
    results = []
    for tag in tags:
        info, error = parse_hashtags(tag)
        assert error is None
        results.append(info.content_type)
    assert set(results) == {kind}


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("#نظري", "theory"),
        ("#مناقشة", "discussion"),
        ("#مناقشه", "discussion"),
        ("#عملي", "lab"),
        ("#رحلة", "field_trip"),
    ],
)
def test_parse_hashtags_section(tag, expected):
    info, error = parse_hashtags(tag)
    assert error is None
    assert info.section == expected


def test_parse_hashtags_glossary_new_alias():
    info, error = parse_hashtags("#المفردات_الدرسية")
    assert error is None
    assert info.content_type == "glossary"


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("#التوصيف", "syllabus"),
        ("#المفردات_الدراسية", "glossary"),
        ("#الواقع_التطبيقي", "practical"),
        ("#مراجع", "references"),
        ("#مهارات", "skills"),
        ("#مشاريع_مفتوحة_المصدر", "open_source_projects"),
    ],
    ids=[
        "التوصيف",
        "المفردات_الدراسية",
        "الواقع_التطبيقي",
        "مراجع",
        "مهارات",
        "مشاريع_مفتوحة_المصدر",
    ],
)
def test_parse_hashtags_content_type(tag, expected):
    info, error = parse_hashtags(tag)
    assert error is None
    assert info.content_type == expected


def test_parse_hashtags_chain_intent():
    info, error = parse_hashtags("#study_plan //follow")
    assert error is None
    assert info.content_type == "study_plan"
    assert info.chain.intent == "follow"
