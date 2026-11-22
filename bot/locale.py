from __future__ import annotations

import json
from pathlib import Path

from config import settings

_LOCALES_DIR = Path(__file__).parent.parent / "locales"
_cache: dict[str, dict] = {}


def get_locale(lang: str) -> dict:
    if lang not in _cache:
        fallback_path = _LOCALES_DIR / "ru.json"
        fallback = json.loads(fallback_path.read_text(encoding="utf-8"))
        path = _LOCALES_DIR / f"{lang}.json"
        if lang == "ru" or not path.exists():
            _cache[lang] = fallback
        else:
            _cache[lang] = {**fallback, **json.loads(path.read_text(encoding="utf-8"))}
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
