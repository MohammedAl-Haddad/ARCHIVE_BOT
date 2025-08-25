import pytest

from bot.utils.formatting import to_display_name


def test_to_display_name_strips_direction_and_underscores():
    raw = "\u200eHello_\u200fWorld"
    assert to_display_name(raw) == "Hello World"

