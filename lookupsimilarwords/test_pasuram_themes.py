#!/usr/bin/env python3
"""Quick checks for pasuram-level theme tagging."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.pasuram_themes import (
    apply_all_themes_to_records,
    apply_mahabharatham_to_records,
    line_triggers_theme,
    load_theme_detector,
    prepare_detector,
)
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR, detector_path_for_theme


def _mb_detector():
    path = detector_path_for_theme("mahabharatham", DEFAULT_DETECTORS_DIR)
    if not path.exists():
        path = Path(__file__).parent / "mahabharatham_detector.json"
    if not path.exists():
        raise FileNotFoundError("Run build_theme_detector.py --theme mahabharatham first")
    return load_theme_detector(path)


def _load_all_detectors() -> List[Dict[str, Any]]:
    detectors: List[Dict[str, Any]] = []
    for path in sorted(DEFAULT_DETECTORS_DIR.glob("*_detector.json")):
        detectors.append(load_theme_detector(path))
    if not detectors:
        raise FileNotFoundError("Run build_theme_detector.py --theme all first")
    return detectors


def _themes_triggered_for_lines(
    lines: List[Dict[str, str]],
    detectors: List[Dict[str, Any]],
) -> Set[str]:
    triggered: Set[str] = set()
    for detector in detectors:
        prepared = prepare_detector(detector)
        theme_id = detector.get("theme_id", "")
        for line in lines:
            matched, _, _ = line_triggers_theme(
                line["Padham"],
                line["Meaning"],
                prepared,
            )
            if matched:
                triggered.add(theme_id)
                break
    return triggered


def _lines_to_records(pasuram_number: int, lines: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    return [
        {
            "PasuramNumber": pasuram_number,
            "PattuNumber": 1,
            "Padham": line["Padham"],
            "Meaning": line["Meaning"],
            "SimilarWords": "title",
        }
        for line in lines
    ]


# Thiruvandhathi snippets from vetting (see thiruvandhathi_*_report.json).
GOLDEN_PASURAMS: Dict[int, Dict[str, Any]] = {
    2213: {
        "expected": {"sangu", "chakkaram"},
        "forbidden": {"sivan"},
        "lines": [
            {"Padham": "மகிழ்ந்தது", "Meaning": "(உன்னைச் சிந்தித்து அதனாலே) ஆநந்த முற்றது;"},
            {"Padham": "மகிழ்ந்தது", "Meaning": "ஆநந்திக்கப்பெற்றது;"},
            {"Padham": "சங்கம்", "Meaning": "ஸ்ரீபாஞ்ச ஜந்யத்தையும்"},
            {"Padham": "ஆழி", "Meaning": "திருவாழியையும்"},
        ],
    },
    2233: {
        "expected": {"ramayana"},
        "forbidden": {"sivan", "vamanan"},
        "lines": [
            {
                "Padham": "செய்ய நெடு மலராள் மார்வன்",
                "Meaning": "சிவந்த நிறத்தையுடையளாய்ப் பெரிய தாமரைப்பூவை யிருப்பிடமாக வுடையளான பெரிய பிராட்டியாரைத் திருமார்விலே யுடையனுமான எம்பெருமான்",
            },
            {
                "Padham": "அரக்கன் போல்வானை",
                "Meaning": "வாட்கையனான இராவணன் போன்ற மஹாபலியை (இராவனைப் போலவே தலையறுக்க வேண்டியிருந்தும் அது செய்யாமல்)",
            },
        ],
    },
    2309: {
        "expected": {"mahabharatham"},
        "forbidden": {"vamanan"},
        "lines": [
            {"Padham": "ஐவர்க்கு ஆய்", "Meaning": "பஞ்சபாண்டவர்களுக்காக"},
            {"Padham": "மத்துக்கே", "Meaning": "மத்துக்காகவாம்,"},
        ],
    },
    2198: {
        "expected": {"sivan"},
        "forbidden": {"gajendran"},
        "lines": [
            {
                "Padham": "ஒற்றை பிறை இருந்த செம்சடையான்",
                "Meaning": "ஓருகலாமாத்திரமான சந்திரனைத் தரித்த சிவந்த சடையையுடைய ருத்ரன்",
            },
            {
                "Padham": "சுற்றும் வணங்கும் தொழிலானை",
                "Meaning": "பக்கங்களிற் சூழ்ந்துகொண்டு ஆச்ரயிப்பதற்கேற்ற சேஷ்டிதங்களை யுடையனான",
            },
        ],
    },
    2272: {
        "expected": {"vamanan"},
        "forbidden": {"ramayana"},
        "lines": [
            {"Padham": "சேராமல்", "Meaning": "அடையாமலிருக்கும் படிக்கு"},
            {
                "Padham": "கார் கடல்சூழ் ஞாலத்தை எல்லாம் அளந்தானவன்",
                "Meaning": "கரிய கடல் சூழப்பட்ட பூமியையெல்லாம் அளந்து கொண்டவனுமான எம்பெருமானுடைய",
            },
        ],
    },
    2194: {
        "expected": {"gajendran", "chakkaram"},
        "forbidden": set(),
        "lines": [
            {
                "Padham": "தொடர் எடுத்த மால் யானை",
                "Meaning": "காற்சங்கிலியை முறித்துக் கையிற்கொண்டு பதறியோடுந் தன்மையதான மதயானையானது",
            },
            {
                "Padham": "ஆழியான் பாதம்",
                "Meaning": "(முதலையைத் துணிக்குங் கருவியான) திருவாழியைக் கையிலேந்தின எம்பெருமானுடைய திருவடிகளை (தியானித்து) வணங்கியதனாலன்றோ",
            },
        ],
    },
    2242: {
        "expected": {"vamanan"},
        "forbidden": {"sivan"},
        "lines": [
            {
                "Padham": "கள்வனே",
                "Meaning": "க்ருத்ரிமனான பெருமானே!",
            },
            {
                "Padham": "இரந்த",
                "Meaning": "(மாவலிபக்கல் மூவடிமண்) யாசித்த",
            },
        ],
    },
    2364: {
        "expected": {"vamanan"},
        "forbidden": {"sivan"},
        "lines": [
            {
                "Padham": "கன்னத்தாள்",
                "Meaning": "க்ருத்ரிம வேஷத்தினால் (மாவலி பக்கலிலே சென்று)",
            },
        ],
    },
    2212: {
        "expected": set(),
        "forbidden": {"vamanan", "sivan"},
        "lines": [
            {
                "Padham": "மணி உருவம்",
                "Meaning": "(அப்பெருமானுடைய) திவ்யமங்கள விக்ரஹத்தை",
            },
        ],
    },
    2310: {
        "expected": set(),
        "forbidden": {"gajendran"},
        "lines": [
            {
                "Padham": "தெருளா மொழியானை",
                "Meaning": "உருத்தெரியாத மழைலைச் சொற்களைச் சொல்லும் சிறு குழந்தையுமான கண்ணபிரானை",
            },
        ],
    },
    2256: {
        "expected": {"gajendran"},
        "forbidden": {"ramayana"},
        "lines": [
            {
                "Padham": "வேழம்",
                "Meaning": "யானையானது",
            },
            {
                "Padham": "இரு கண் இளமூங்கில் வாங்கி",
                "Meaning": "இரண்டு கணுக்களையுடைத்தாய் இளையதான மூங்கில் குருத்தைப்பிடுங்கி",
            },
        ],
    },
    2270: {
        "expected": {"vamanan"},
        "forbidden": {"gajendran"},
        "lines": [
            {
                "Padham": "போர் யானை",
                "Meaning": "போர் செய்வதாக எதிர்த்துவந்த குவலயாபீடமென்னும் யானையை",
            },
            {
                "Padham": "மாவலியை",
                "Meaning": "மஹாபலியினிடத்திலே",
            },
        ],
    },
    2199: {
        "expected": {"narasimha"},
        "forbidden": {"garudan"},
        "lines": [
            {"Padham": "கோள் அரி ஆய்", "Meaning": "மிடுக்கையுடைய நரசிங்கமாகி"},
            {"Padham": "ஒண்திறலோன் மார்வத்து", "Meaning": "மஹா பலசாலியான இரணியனுடைய மார்பிலே"},
        ],
    },
    2338: {
        "expected": {"garudan"},
        "forbidden": {"narasimha"},
        "lines": [
            {"Padham": "பொலிந்த கருடன் மேல் கொண்ட", "Meaning": "விளங்குகின்ற கருடனால் மேற்றகொள்ளப்பட்டவனான"},
        ],
    },
    2244: {
        "expected": set(),
        "forbidden": {"garudan"},
        "lines": [
            {
                "Padham": "எரி உருவத்து ஏறு ஏறிபட்ட",
                "Meaning": "நெருப்புப்போன்ற உருவத்தையுடையவனும் வருஷப வாஹநனுமான ருத்ரன் அநுபவித்த",
            },
        ],
    },
    2226: {
        "expected": set(),
        "forbidden": {"narasimha"},
        "lines": [
            {
                "Padham": "அளவு அரிய வேதத்தான்",
                "Meaning": "அளவிட முடியாதபடி அந்நதமாயுள்ள வேதங்களினால் பிரதிபாதிக்கப்படு",
            },
        ],
    },
}


def test_pasuram_80_style_group():
    detector = _mb_detector()
    records = [
        {"PasuramNumber": 80, "PattuNumber": 6, "Padham": "தந்தை", "Meaning": "(எல்லார்க்கும்) பிதாவாகிய உனது", "SimilarWords": "தந்தை,Thandai, title"},
        {"PasuramNumber": 80, "PattuNumber": 6, "Padham": "பஞ்சவர்க்கு", "Meaning": "பஞ்ச பாண்டவர்களுக்கு (வெற்றி உண்டாக)", "SimilarWords": "பஞ்சவர்க்கு,Panjavarkku, title"},
    ]
    out = apply_mahabharatham_to_records(records, detector)
    assert all("மகாபாரதம்" in r["SimilarWords"] for r in out), "all rows in pasuram 80 should get MB"
    print("OK pasuram 80 style: all rows tagged when one strong line present")


def test_generic_pasuram_not_tagged():
    detector = _mb_detector()
    records = [
        {"PasuramNumber": 9999, "PattuNumber": 1, "Padham": "தந்தை", "Meaning": "(எல்லார்க்கும்) பிதாவாகிய உனது", "SimilarWords": "தந்தை,Thandai, title"},
        {"PasuramNumber": 9999, "PattuNumber": 1, "Padham": "சொல்", "Meaning": "பேச்சை", "SimilarWords": "சொல்,Sol, title"},
    ]
    out = apply_mahabharatham_to_records(records, detector)
    assert all("மகாபாரதம்" not in r["SimilarWords"] for r in out), "generic-only pasuram should not tag"
    print("OK generic pasuram: no MB when no strong signal")


def test_multi_theme_union():
    mb = {
        "theme_id": "mahabharatham",
        "aliases": ["மகாபாரதம்", "mahabharatham"],
        "normalize_meaning_parenthesis": True,
        "meaning_keywords": ["பாரத"],
        "padham_substring_signals": ["பஞ்சவர்"],
    }
    ram = {
        "theme_id": "ramayana",
        "aliases": ["Ramayanam", "இராமாயணம்", "Raman", "இராமன்", "காகுத்தன்", "Kaguthan"],
        "meaning_keywords": ["இராமன்"],
        "padham_substring_signals": ["இராமன்"],
    }
    records = [
        {"PasuramNumber": 2916, "PattuNumber": 1, "Padham": "பஞ்சவர்", "Meaning": "generic", "SimilarWords": "பஞ்சவர், title"},
        {"PasuramNumber": 2916, "PattuNumber": 1, "Padham": "தந்தை", "Meaning": "generic", "SimilarWords": "தந்தை, title"},
        {"PasuramNumber": 2916, "PattuNumber": 1, "Padham": "இராமன்", "Meaning": "இராமன் அவதாரம்", "SimilarWords": "இராமன், title"},
    ]
    out = apply_all_themes_to_records(records, [mb, ram])
    expected = [
        "மகாபாரதம்",
        "mahabharatham",
        "Ramayanam",
        "இராமாயணம்",
        "Raman",
        "இராமன்",
        "காகுத்தன்",
        "Kaguthan",
    ]
    for alias in expected:
        assert all(alias in r["SimilarWords"] for r in out), f"missing {alias} on multi-theme pasuram"
    print("OK multi-theme: MB + Ramayana aliases unioned on all rows")


def test_ramayana_sanskrit_stems():
    """Periya Thirumozhi 1418-style glosses use ஸீதை / லக்ஷ்மணன் / ஸ்ரீராமாவதார (not சீத alone)."""
    ram = load_theme_detector(detector_path_for_theme("ramayana", DEFAULT_DETECTORS_DIR))
    prepared = prepare_detector(ram)
    cases = [
        ("மாழை மான் மட நோக்கி", "என் மனைவியாகிய இந்த ஸீதை"),
        ("எம்பி", "என் தம்பியான லக்ஷ்மணன்"),
        ("என்ற", "(நீ ஸ்ரீராமாவதாரத்திற்) சொல்லியருளிய"),
    ]
    for padham, meaning in cases:
        matched, reason, term = line_triggers_theme(padham, meaning, prepared)
        assert matched, f"expected Ramayana hit for {meaning[:40]!r}, got none"
        assert reason == "meaning_keyword", reason
        assert term, term
    print("OK ramayana: ஸீத / லக்ஷ்மண / ஸ்ரீராம meaning stems")


def test_blocked_substring_guards():
    sivan = load_theme_detector(detector_path_for_theme("sivan", DEFAULT_DETECTORS_DIR))
    prepared = prepare_detector(sivan)
    matched, _, term = line_triggers_theme(
        "செய்ய நெடு மலராள் மார்வன்",
        "சிவந்த நிறத்தையுடையளாய்ப் பெரிய தாமரைப்பூவை",
        prepared,
    )
    assert not matched, f"சிவந்த should not trigger sivan, got {term}"
    matched, _, term = line_triggers_theme(
        "மகிழ்ந்தது",
        "(உன்னைச் சிந்தித்து அதனாலே) ஆநந்த முற்றது;",
        prepared,
    )
    assert not matched, f"ஆநந்த should not trigger sivan, got {term}"
    matched, _, term = line_triggers_theme(
        "மகிழ்ந்தது",
        "ஆநந்திக்கப்பெற்றது;",
        prepared,
    )
    assert not matched, f"ஆநந்திக்க should not trigger நந்தி, got {term}"
    print("OK sivan guards: சிவந்த, ஆநந்த, ஆநந்திக்க blocked")


def test_golden_thiruvandhathi_pasurams():
    detectors = _load_all_detectors()
    for pasuram_number, spec in GOLDEN_PASURAMS.items():
        triggered = _themes_triggered_for_lines(spec["lines"], detectors)
        expected = set(spec["expected"])
        forbidden = set(spec.get("forbidden", []))
        assert expected <= triggered, (
            f"pasuram {pasuram_number}: missing {expected - triggered}, got {triggered}"
        )
        overlap = forbidden & triggered
        assert not overlap, (
            f"pasuram {pasuram_number}: false positives {overlap}, got {triggered}"
        )
        print(f"OK golden pasuram {pasuram_number}: {sorted(triggered)}")


def test_siriya_thirumadal_vamana_pattu6():
    vamanan = load_theme_detector(detector_path_for_theme("vamanan", DEFAULT_DETECTORS_DIR))
    prepared = prepare_detector(vamanan)
    matched, reason, term = line_triggers_theme(
        "இ வையம் ஆரால் அடி அளப்புண்டது",
        "யாவனொருவனாலே இப்பூமியானது அளக்கப்பட்டதோ.",
        prepared,
    )
    assert matched, "Pattu 6 padham/meaning should trigger vamanan"
    assert reason in {"padham_substring", "meaning_keyword"}, reason
    assert term in {"அளப்ப", "அளக்க", "அடி அள"}, term
    print("OK siriya thirumadal pattu 6 vamana padham/meaning")


def test_per_pattu_theme_grouping():
    vamanan = load_theme_detector(detector_path_for_theme("vamanan", DEFAULT_DETECTORS_DIR))
    records = [
        {
            "PasuramNumber": 2673,
            "PattuNumber": 6,
            "Padham": "இ வையம் ஆரால் அடி அளப்புண்டது",
            "Meaning": "யாவனொருவனாலே இப்பூமியானது அளக்கப்பட்டதோ.",
            "SimilarWords": "test",
        },
        {
            "PasuramNumber": 2673,
            "PattuNumber": 7,
            "Padham": "சில பதம்",
            "Meaning": "சில அர்த்தம்",
            "SimilarWords": "test",
        },
    ]
    out = apply_all_themes_to_records(records, [vamanan])
    p6 = [r for r in out if r["PattuNumber"] == 6][0]
    p7 = [r for r in out if r["PattuNumber"] == 7][0]
    assert "vamanan" in p6["SimilarWords"].lower()
    assert "vamanan" not in p7["SimilarWords"].lower()
    print("OK per-pattu grouping: vamanan only on pattu 6")


if __name__ == "__main__":
    test_pasuram_80_style_group()
    test_generic_pasuram_not_tagged()
    test_multi_theme_union()
    test_ramayana_sanskrit_stems()
    test_blocked_substring_guards()
    test_siriya_thirumadal_vamana_pattu6()
    test_per_pattu_theme_grouping()
    test_golden_thiruvandhathi_pasurams()
