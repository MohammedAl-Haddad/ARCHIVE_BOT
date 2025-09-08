from pathlib import Path
import json
from typing import Dict, Any

_BASE = Path(__file__).resolve().parent


class Translator:
    def __init__(self, default: str = "en") -> None:
        self.default = default
        self._cache: Dict[str, Dict[str, str]] = {}

    def _load(self, lang: str) -> None:
        path = _BASE / f"messages_{lang}.json"
        with path.open(encoding="utf-8") as fh:
            self._cache[lang] = json.load(fh)

    def gettext(
        self,
        key: str,
        user_settings: Dict[str, Any] | None = None,
        *,
        lang: str | None = None,
    ) -> str:
        if lang is None:
            lang = (user_settings or {}).get("lang", self.default)
        if lang not in self._cache:
            self._load(lang)
        return self._cache[lang].get(key, key)


_default_translator = Translator()


def get_text(
    key: str,
    user_settings: Dict[str, Any] | None = None,
    *,
    lang: str | None = None,
) -> str:
    return _default_translator.gettext(key, user_settings, lang=lang)


__all__ = ["Translator", "get_text"]
