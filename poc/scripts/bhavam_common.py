"""Shared bhavam constants. Verse tags come from Tableau Pasuram-Nu, not Padham."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
COMPASS_JSON = ROOT / "poc" / "data" / "bhavam_tableau_compass.json"
TABLEAU_CSV = ROOT / "poc" / "data" / "bhavam_tableau.csv"
OUT_JSON = ROOT / "public_html" / "data" / "bhavam_reports_poc.json"

BHAVAM_ALIASES: Dict[str, List[str]] = {
    "Mother": ["தாய் பாவம்"],
    "Nayaki": ["நாயகி பாவம்"],
    "Thozhi": ["தோழி பாவம்"],
}

SKIP_ROLES = frozenset({"Male", "male", "ஆண்"})

ROLE_NORMALIZE = {
    "mother": "Mother",
    "தாய்": "Mother",
    "தாய் பாவம்": "Mother",
    "nayaki": "Nayaki",
    "நாயகி": "Nayaki",
    "நாயகி பாவம்": "Nayaki",
    "thozhi": "Thozhi",
    "தோழி": "Thozhi",
    "தோழி பாவம்": "Thozhi",
}

PRABANDHAM_EN_TA: Dict[str, str] = {
    "thirupallandu": "திருப்பல்லாண்டு",
    "periyazhwar thirumozhi": "பெரியாழ்வார் திருமொழி",
    "thiruppavai": "திருப்பாவை",
    "nachiar thirumozhi": "நாச்சியார் திருமொழி",
    "nachchiar thirumozhi": "நாச்சியார் திருமொழி",
    "perumal thirumozhi": "பெருமாள் திருமொழி",
    "thiruvaimozhi": "திருவாய்மொழி",
    "thiruvaiozmhi": "திருவாய்மொழி",
    "thiruvirutham": "திருவிருத்தம்",
    "periya thirumozhi": "பெரிய திருமொழி",
    "thirunedunthaandagam": "திரு நெடும் தாண்டகம்",
    "thirunedunthandagam": "திரு நெடும் தாண்டகம்",
    "siriya thirumadal": "சிறிய திருமடல்",
    "periya thirumadal": "பெரிய திருமடல்",
    "mudhal thiruvandadhi": "முதல் திருவந்தாதி",
    "mudhal thiruvandhadhi": "முதல் திருவந்தாதி",
}


def normalize_role(raw: str) -> str:
    key = (raw or "").strip()
    if not key:
        return ""
    return ROLE_NORMALIZE.get(key.lower(), ROLE_NORMALIZE.get(key, key))


def aliases_for_role(role: str) -> List[str]:
    return list(BHAVAM_ALIASES.get(role, []))


def prabandham_ta(english: str) -> str:
    return PRABANDHAM_EN_TA.get((english or "").strip().lower(), "")
