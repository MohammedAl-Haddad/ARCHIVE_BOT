import pytest

from bot.utils.formatting import to_display_name, format_lecturer_name


def test_to_display_name_strips_direction_and_underscores():
    raw = "\u200eHello_\u200fWorld"
    assert to_display_name(raw) == "Hello World"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("صالح", "الدكتور صالح"),
        ("الدكتور صالح", "الدكتور صالح"),
        ("د. صالح", "د. صالح"),
    ],
)
def test_format_lecturer_name(raw: str, expected: str) -> None:
    assert format_lecturer_name(raw) == expected

