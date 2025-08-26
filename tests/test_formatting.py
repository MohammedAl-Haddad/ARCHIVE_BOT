import pytest

from bot.utils.formatting import to_display_name, add_lecturer_title


def test_to_display_name_strips_direction_and_underscores():
    raw = "\u200eHello_\u200fWorld"
    assert to_display_name(raw) == "Hello World"


def test_add_lecturer_title_adds_prefix_when_missing():
    assert add_lecturer_title("فلان") == "الدكتور فلان"


def test_add_lecturer_title_keeps_existing():
    assert add_lecturer_title("الدكتور علان") == "الدكتور علان"

