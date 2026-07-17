#!/usr/bin/env python3
"""Mine and review candidate detector signals from POC rows tagged with a theme."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.extract_concept_lookup import build_record, normalize_text, query_concept_rows
from lookupsimilarwords.pasuram_themes import line_triggers_theme, load_theme_detector, prepare_detector
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR, detector_path_for_theme, get_theme


# Ramayana-specific meaning stems to surface for human review (not auto-applied)
THEME_REVIEW_STEMS: Dict[str, List[str]] = {
    "sivan": [
        "சிவ", "siva", "sivan", "rudra", "ருத்ர", "நமச்ச", "namach", "பஞ்சாட்ச", "panchaksh",
        "சங்கர", "sankar", "pasupati", "பசுப", "கயில", "kail", "நந்த", "nandi", "ஜட", "jata", "ஜடை", "சடை",
    ],
    "gajendran": [
        "கஜ", "gaj", "gajendra", "யானை", "yaanai", "elephant", "களிற", "kaliri", "mudalai", "முதல",
        "எரும", "erumbu", "வேழ", "vezhah", "நிவர்த", "nivartana", "அலக", "alag",
    ],
    "sangu": [
        "சங்க", "sangu", "sankha", "conch", "பாஞ்ச", "panchaj", "panca", "வலம்", "valam", "வலம்ப", "valamp", "ஜன்ய",
    ],
    "chakkaram": [
        "சக்க", "chakk", "chakram", "chakara", "நேம", "nemi", "ஆழ", "aazhi", "aazh", "திருவாழ", "tiruvazh",
        "sudarsh", "சுட", "சக்கரபாண",
    ],
    "ramayana": [
        "இராம", "ராம", "raman", "ramayan", "காகுத்த", "kaguthan", "சீத", "sita", "sitai",
        "இலங்க", "ilangai", "lanka", "அரக்க", "arakkar", "rakshas", "ரavan", "ராவண",
        "அனும", "hanuman", "குரங்க", "kurangu", "அணை கட்ட", "sethu", "setu", "மாயமா", "இளைய",
    ],
    "vamanan": [
        "வாம", "vama", "vaman", "வாமந", "திருவிக", "thiruvik", "vikram", "விக்ர", "மாவலி", "mavali",
        "mahabali", "mahapali", "பலி", "bali", "அளந்த", "alanthan", "அமண", "amana", "amanan", "மூவட",
    ],
    "narasimha": [
        "நரசிம்", "நரசிங்", "narasim", "narsim", "narasing", "narasimhan", "narasimhar",
        "இரணிய", "hiranya", "ஹிரண்ய", "ஹரண்ய", "prahlada", "ப்ரஹ்லாத", "பிரஹ்லாத",
        "அரி உருவ", "அரி ஆய்", "சிங்கம் ஆய்", "நரஸிம்ம",
    ],
    "garudan": [
        "கருட", "garud", "garuda", "karuda", "பெரிய திருவடி", "periya thiruvadi",
        "கொடிமேல் புள்", "புள் ஊர்", "புள்ளை ஊர்", "கருடபக்ஷி",
    ],
}


def primary_tagged_rows(raw_rows: List[Dict[str, Any]], theme_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    aliases = theme_config.get("aliases", [])
    if not aliases:
        return raw_rows
    filtered = []
    for r in raw_rows:
        sw = r.get("SimilarWords") or ""
        sw_l = sw.lower()
        if any(a in sw or a.lower() in sw_l for a in aliases):
            filtered.append(r)
    return filtered

def alias_seeds(theme_config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    meaning = list(theme_config.get("meaning_keyword_seeds", []))
    padham = list(theme_config.get("padham_substring_seeds", []))
    return meaning, padham


def stem_hits(text: str, stems: List[str]) -> List[str]:
    text_l = normalize_text(text).lower()
    hits: List[str] = []
    for stem in stems:
        s = normalize_text(stem).lower()
        if s and s in text_l:
            hits.append(stem)
    return hits


def classify_line(
    padham: str,
    meaning: str,
    alias_meaning: List[str],
    alias_padham: List[str],
    review_stems: List[str],
    prepared_detector: Dict[str, Any] | None,
) -> Dict[str, Any]:
    padham = normalize_text(padham)
    meaning = normalize_text(meaning)

    detector_match = False
    detector_reason = ""
    detector_term = ""
    if prepared_detector:
        detector_match, detector_reason, detector_term = line_triggers_theme(
            padham, meaning, prepared_detector
        )

    alias_m = [s for s in alias_meaning if normalize_text(s).lower() in meaning.lower()]
    alias_p = [s for s in alias_padham if normalize_text(s).lower() in padham.lower()]
    review_m = stem_hits(meaning, review_stems)
    review_p = stem_hits(padham, review_stems)

    if detector_match:
        strength = "detector_match"
    elif alias_m or alias_p:
        strength = "alias_match"
    elif review_m or review_p:
        strength = "thematic_candidate"
    else:
        strength = "weak_pasuram_only"

    return {
        "padham": padham,
        "meaning": meaning,
        "meaning_snippet": meaning[:120],
        "strength": strength,
        "detector_match": detector_match,
        "detector_reason": detector_reason,
        "detector_term": detector_term,
        "alias_hits_meaning": alias_m,
        "alias_hits_padham": alias_p,
        "review_stems_meaning": review_m,
        "review_stems_padham": review_p,
    }


def build_review(
    theme_id: str,
    db_config: Dict[str, Any],
    review_stems: List[str],
    detector_path: Path | None,
) -> Dict[str, Any]:
    theme_config = get_theme(theme_id)
    query_concepts = theme_config.get("query_concepts", [theme_config.get("concept", theme_id)])
    primary_tag = "Ramayanam" if theme_id == "ramayana" else theme_config.get("aliases", [""])[0]

    raw_rows = query_concept_rows(db_config, query_concepts)
    raw_rows = primary_tagged_rows(raw_rows, theme_config)

    alias_meaning, alias_padham = alias_seeds(theme_config)
    prepared = None
    if detector_path and detector_path.exists():
        prepared = prepare_detector(load_theme_detector(detector_path))

    by_pasuram: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        rec = build_record(row)
        if rec:
            by_pasuram[rec["PasuramNumber"]].append(rec)

    pasuram_summaries: List[Dict[str, Any]] = []
    meaning_stem_counter: Counter = Counter()
    padham_stem_counter: Counter = Counter()
    padham_exact_counter: Counter = Counter()

    for pasuram_num in sorted(by_pasuram.keys(), key=lambda x: (isinstance(x, str), x)):
        lines_out: List[Dict[str, Any]] = []
        for rec in by_pasuram[pasuram_num]:
            cls = classify_line(
                rec["Padham"],
                rec["Meaning"],
                alias_meaning,
                alias_padham,
                review_stems,
                prepared,
            )
            lines_out.append(cls)
            for s in cls["review_stems_meaning"]:
                meaning_stem_counter[s] += 1
            for s in cls["review_stems_padham"]:
                padham_stem_counter[s] += 1
            if cls["strength"] in ("detector_match", "alias_match", "thematic_candidate"):
                padham_exact_counter[rec["Padham"]] += 1

        strong_lines = [l for l in lines_out if l["strength"] != "weak_pasuram_only"]
        detector_would_tag = any(l["detector_match"] for l in lines_out)

        pasuram_summaries.append(
            {
                "pasuram_number": pasuram_num,
                "line_count": len(lines_out),
                "strong_line_count": len(strong_lines),
                "detector_would_tag": detector_would_tag,
                "strong_lines": strong_lines,
                "sample_weak_padhams": [
                    l["padham"] for l in lines_out if l["strength"] == "weak_pasuram_only"
                ][:5],
            }
        )

    candidate_meaning_keywords = [
        {"stem": s, "line_hits": c}
        for s, c in meaning_stem_counter.most_common()
        if s not in alias_meaning
    ]
    candidate_padham_signals = [
        {"stem": s, "line_hits": c}
        for s, c in padham_stem_counter.most_common()
        if s not in alias_padham
    ]
    top_thematic_padhams = [
        {"padham": p, "strong_line_hits": c}
        for p, c in padham_exact_counter.most_common(40)
    ]

    return {
        "theme_id": theme_id,
        "primary_similarwords_tag": primary_tag,
        "source_table": db_config["table"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "pasuram_count": len(pasuram_summaries),
        "detector_would_tag_count": sum(1 for p in pasuram_summaries if p["detector_would_tag"]),
        "candidate_meaning_keywords": candidate_meaning_keywords,
        "candidate_padham_substrings": candidate_padham_signals,
        "top_thematic_padhams": top_thematic_padhams,
        "pasurams": pasuram_summaries,
    }


def save_pasuram_csv(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pasuram_number",
        "detector_would_tag",
        "strong_line_count",
        "line_count",
        "strength",
        "padham",
        "meaning_snippet",
        "detector_reason",
        "detector_term",
        "alias_hits",
        "review_stems",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for pasuram in report["pasurams"]:
            for line in pasuram.get("strong_lines", []):
                writer.writerow(
                    {
                        "pasuram_number": pasuram["pasuram_number"],
                        "detector_would_tag": pasuram["detector_would_tag"],
                        "strong_line_count": pasuram["strong_line_count"],
                        "line_count": pasuram["line_count"],
                        "strength": line["strength"],
                        "padham": line["padham"],
                        "meaning_snippet": line["meaning_snippet"],
                        "detector_reason": line.get("detector_reason") or "",
                        "detector_term": line.get("detector_term") or "",
                        "alias_hits": "; ".join(
                            line.get("alias_hits_padham", []) + line.get("alias_hits_meaning", [])
                        ),
                        "review_stems": "; ".join(
                            line.get("review_stems_padham", []) + line.get("review_stems_meaning", [])
                        ),
                    }
                )


def save_candidates_csv(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["kind", "signal", "line_hits"])
        writer.writeheader()
        for item in report.get("candidate_meaning_keywords", []):
            writer.writerow({"kind": "meaning_keyword", "signal": item["stem"], "line_hits": item["line_hits"]})
        for item in report.get("candidate_padham_substrings", []):
            writer.writerow({"kind": "padham_substring", "signal": item["stem"], "line_hits": item["line_hits"]})
        for item in report.get("top_thematic_padhams", []):
            writer.writerow(
                {
                    "kind": "thematic_padham",
                    "signal": item["padham"],
                    "line_hits": item["strong_line_hits"],
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review candidate theme signals from POC tags")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--theme", default="ramayana")
    parser.add_argument("--detectors-dir", default=str(DEFAULT_DETECTORS_DIR))
    parser.add_argument("--output-dir", default="lookupsimilarwords/reviews")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_config = load_db_config(Path(args.config))
    theme_id = args.theme
    detector_path = detector_path_for_theme(theme_id, Path(args.detectors_dir))

    review_stems = THEME_REVIEW_STEMS.get(theme_id, [])

    report = build_review(theme_id, db_config, review_stems, detector_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{theme_id}_signal_review.json"
    pasuram_csv = out_dir / f"{theme_id}_strong_lines_review.csv"
    candidates_csv = out_dir / f"{theme_id}_candidate_signals.csv"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    save_pasuram_csv(report, pasuram_csv)
    save_candidates_csv(report, candidates_csv)

    print(f"Theme: {theme_id}")
    print(f"Pasurams with {report['primary_similarwords_tag']}: {report['pasuram_count']}")
    print(f"Current detector would tag: {report['detector_would_tag_count']}/{report['pasuram_count']}")
    print(f"\nTop candidate meaning stems (for review):")
    for item in report["candidate_meaning_keywords"][:15]:
        print(f"  {item['line_hits']:4d}  {item['stem']}")
    print(f"\nTop candidate padham stems:")
    for item in report["candidate_padham_substrings"][:15]:
        print(f"  {item['line_hits']:4d}  {item['stem']}")
    print(f"\nWrote {json_path}")
    print(f"Wrote {pasuram_csv}")
    print(f"Wrote {candidates_csv}")


if __name__ == "__main__":
    main()
