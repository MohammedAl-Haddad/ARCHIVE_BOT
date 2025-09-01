from bot.keyboards.builders.paginated import build_children_keyboard


def _make_children(n: int):
    return [("kind", i, f"Item {i}") for i in range(1, n + 1)]


def test_build_children_keyboard_first_page():
    children = _make_children(5)
    markup = build_children_keyboard(children, page=1, per_page=2)
    # two items on first page
    assert markup.inline_keyboard[0][0].callback_data == "nav:kind:1"
    assert markup.inline_keyboard[0][1].callback_data == "nav:kind:2"
    # navigation row should point to next page only
    assert markup.inline_keyboard[1][0].callback_data == "nav:page:2"
    # back button exists
    assert markup.inline_keyboard[2][0].callback_data == "nav:back"


def test_build_children_keyboard_middle_page():
    children = _make_children(5)
    markup = build_children_keyboard(children, page=2, per_page=2)
    # items 3 and 4
    assert markup.inline_keyboard[0][0].callback_data == "nav:kind:3"
    assert markup.inline_keyboard[0][1].callback_data == "nav:kind:4"
    # navigation row has prev and next
    assert [b.callback_data for b in markup.inline_keyboard[1]] == ["nav:page:1", "nav:page:3"]
    # back button
    assert markup.inline_keyboard[2][0].callback_data == "nav:back"
