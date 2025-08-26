import pytest

from bot.parser import extract_hijri_year


def test_extract_hijri_year_parses_arabic_digits():
    assert extract_hijri_year("سنة #١٤٤٦هـ") == 1446


def test_extract_hijri_year_returns_none_when_absent():
    assert extract_hijri_year("لا يوجد سنة هنا") is None
