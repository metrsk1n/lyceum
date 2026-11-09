from __future__ import annotations

import json
from pathlib import Path

from config import settings

_LOCALES_DIR = Path(__file__).parent.parent / "locales"
_cache: dict[str, dict] = {}


def get_locale(lang: str) -> dict:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            path = _LOCALES_DIR / "ru.json"
        _cache[lang] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[lang]


def t(lang: str, key: str, **kwargs) -> str:
    """Get translated text by dot-notation key."""
    locale = get_locale(lang)
    value = locale
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return key
    if isinstance(value, str):
        return value.format(**kwargs) if kwargs else value
    return str(value)
