import pytest

from bot.parser.hashtags import parse_hashtags, TERM_RESOURCE_ALIASES


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


@pytest.mark.parametrize(
    "tag, expected",
    [
        (f"#{alias}", kind)
        for kind, aliases in TERM_RESOURCE_ALIASES.items()
        for alias in aliases
    ],
)
def test_parse_hashtags_term_resources(tag, expected):
    info, error = parse_hashtags(tag)
    assert error is None
    assert info.content_type == expected
