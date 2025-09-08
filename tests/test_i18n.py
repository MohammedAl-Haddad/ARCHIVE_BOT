from bot.i18n.translator import Translator, get_text


def test_translator_fetches_correct_language():
    t = Translator()
    assert t.gettext("hello", {"lang": "en"}) == "Hello"
    assert t.gettext("hello", {"lang": "ar"}) == "مرحبا"


def test_get_text_wrapper():
    assert get_text("bye", {"lang": "ar"}) == "مع السلامة"
    assert get_text("unknown", {"lang": "en"}) == "unknown"

