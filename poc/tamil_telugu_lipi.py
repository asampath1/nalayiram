"""Deterministic Tamil → Telugu lipi (script conversion, not translation)."""
from __future__ import annotations

import re
import unicodedata

# Substring locks applied on Tamil source before the letter map.
LOCKED_PHRASES: tuple[tuple[str, str], ...] = (
    ("திருப்பல்லாண்டு", "తిరుప్పల్లాండు"),
    ("பெரியாழ்வார்", "పెరియాళ్వార్"),
    ("ஆழ்வார்", "ఆళ్వార్"),
    ("ஸ்ரீரங்கம்", "శ్రీరంగం"),
    ("ஸ்ரీ", "శ్రీ"),
    ("பல்லாண்டு", "పల్లాండు"),
)

# Lossy or non-offset Tamil letters.
_EXCEPTIONS: dict[str, str] = {
    "ன": "న",
    "ழ": "ళ",
    "ஃ": "ః",
}

_TAMIL_BLOCK = range(0x0B80, 0x0BE0)
_TAMIL_DIGITS = range(0x0BE6, 0x0BF0)
_OFFSET = 0x80


def _map_char(ch: str) -> str:
    if ch in _EXCEPTIONS:
        return _EXCEPTIONS[ch]
    cp = ord(ch)
    if cp in _TAMIL_BLOCK or cp in _TAMIL_DIGITS:
        mapped = chr(cp + _OFFSET)
        if unicodedata.category(mapped) == "Cn":
            return ch
        return mapped
    return ch


def tamil_to_telugu_lipi(text: str | None) -> str:
    """Convert Tamil letters to Telugu letters. ASCII and punctuation stay."""
    if not text:
        return ""
    out = text.replace("\u200c", "").replace("\u200d", "")
    for ta, te in LOCKED_PHRASES:
        out = out.replace(ta, te)
    out = "".join(_map_char(ch) for ch in out)
    # Tamil ண்ட is voiced; letter-map yields ణ్ట / ణ్డ.
    out = out.replace("ణ్ట", "ండ").replace("ణ్డ", "ండ")
    return out


_WS = re.compile(r"\s+")


def whitespace_tokens(text: str | None) -> list[str]:
    if not text:
        return []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [t for t in _WS.split(normalized.strip()) if t]


def token_count_ok(tamil: str | None, telugu: str | None) -> bool:
    return len(whitespace_tokens(tamil)) == len(whitespace_tokens(telugu))
