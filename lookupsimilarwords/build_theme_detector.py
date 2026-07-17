#!/usr/bin/env python3
"""Build theme detector signals from POC rows already tagged with theme aliases in SimilarWords."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.extract_concept_lookup import build_record, normalize_text, query_concept_rows
from lookupsimilarwords.pasuram_themes import line_triggers_theme, normalize_meaning_for_theme, prepare_detector
from lookupsimilarwords.theme_registry import (
    DEFAULT_DETECTORS_DIR,
    detector_path_for_theme,
    get_theme,
    list_theme_ids,
    load_theme_registry,
    resolve_theme_ids,
)


def meaning_matches_seed(meaning: str, seeds: List[str], unwrap_parenthesis: bool) -> List[str]:
    meaning_n = normalize_meaning_for_theme(meaning, unwrap_parenthesis=unwrap_parenthesis).lower()
    hits: List[str] = []
    for seed in seeds:
        seed_n = normalize_text(seed).lower()
        if seed_n and seed_n in meaning_n:
            hits.append(seed)
    return hits


def padham_matches_substring(padham: str, seeds: List[str]) -> List[str]:
    padham_n = normalize_text(padham).lower()
    hits: List[str] = []
    for seed in seeds:
        seed_n = normalize_text(seed).lower()
        if seed_n and seed_n in padham_n:
            hits.append(seed)
    return hits


def is_strong_theme_line(
    padham: str,
    meaning: str,
    meaning_seeds: List[str],
    padham_seeds: List[str],
    unwrap_parenthesis: bool,
) -> tuple[bool, str]:
    meaning_hits = meaning_matches_seed(meaning, meaning_seeds, unwrap_parenthesis)
    if meaning_hits:
        return True, f"meaning:{meaning_hits[0]}"

    padham_hits = padham_matches_substring(padham, padham_seeds)
    if padham_hits:
        return True, f"padham:{padham_hits[0]}"

    return False, ""


def finalize_detector_from_registry(
    detector: Dict[str, Any],
    theme_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply registry guard config and drop excluded short stems from mined lists."""
    excluded = {
        normalize_text(s).lower()
        for s in theme_config.get("excluded_stems", [])
        if normalize_text(s)
    }

    def _filter_terms(terms: Set[str]) -> List[str]:
        kept: Set[str] = set()
        for term in terms:
            term_n = normalize_text(term)
            if not term_n:
                continue
            if term_n.lower() in excluded:
                continue
            kept.add(term_n)
        return sorted(kept, key=lambda x: (len(x), x))

    detector["meaning_keywords"] = _filter_terms(set(detector.get("meaning_keywords", [])))
    detector["padham_substring_signals"] = _filter_terms(
        set(detector.get("padham_substring_signals", []))
    )

    for key in (
        "min_stem_length",
        "blocked_contexts",
        "meaning_only_excluded_stems",
        "excluded_stems_review",
    ):
        if key in theme_config:
            detector[key] = theme_config[key]

    return detector


def build_detector_from_records(
    records: List[Dict[str, Any]],
    theme_id: str,
    theme_config: Dict[str, Any],
    source_table: str,
) -> Dict[str, Any]:
    meaning_seeds = list(theme_config.get("meaning_keyword_seeds", []))
    padham_seeds = list(theme_config.get("padham_substring_seeds", []))
    unwrap = bool(theme_config.get("normalize_meaning_parenthesis", False))

    meaning_keywords: Set[str] = set(meaning_seeds)
    padham_substring_signals: Set[str] = set(padham_seeds)
    padham_substring_only: Set[str] = set()

    strong_line_count = 0
    weak_line_count = 0

    for record in records:
        padham = normalize_text(record.get("Padham", ""))
        meaning = normalize_text(record.get("Meaning", ""))
        if not padham:
            continue

        strong, _reason = is_strong_theme_line(
            padham, meaning, meaning_seeds, padham_seeds, unwrap
        )
        if strong:
            strong_line_count += 1
            for hit in meaning_matches_seed(meaning, meaning_seeds, unwrap):
                meaning_keywords.add(hit)
            padham_hits = padham_matches_substring(padham, padham_seeds)
            for hit in padham_hits:
                padham_substring_signals.add(hit)
            if padham_hits and not meaning_matches_seed(meaning, meaning_seeds, unwrap):
                padham_substring_only.add(padham)
        else:
            weak_line_count += 1

    concept = theme_config.get("concept", theme_id)
    aliases = list(theme_config.get("aliases", [concept]))

    detector = {
        "theme_id": theme_id,
        "concept": concept,
        "aliases": aliases,
        "normalize_meaning_parenthesis": unwrap,
        "source_table": source_table,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "description": (
            f"Detector mined from POC rows with {concept} theme in SimilarWords. "
            "Match via padham_substring_signals on Padham OR meaning_keywords on Meaning only "
            "(no global padham-exact list)."
        ),
        "stats": {
            "tagged_rows_analyzed": len(records),
            "strong_signal_lines": strong_line_count,
            "weak_pasuram_only_lines": weak_line_count,
            "padham_substring_signal_count": len(padham_substring_signals),
            "meaning_keyword_count": len(meaning_keywords),
            "distinct_pasurams_in_source": len(
                {r.get("PasuramNumber") for r in records if r.get("PasuramNumber") is not None}
            ),
        },
        "meaning_keywords": sorted(meaning_keywords, key=lambda x: (len(x), x)),
        "padham_substring_signals": sorted(padham_substring_signals, key=lambda x: (len(x), x)),
        "padham_substring_only_review": sorted(padham_substring_only),
    }
    detector = finalize_detector_from_registry(detector, theme_config)
    detector["stats"]["padham_substring_signal_count"] = len(
        detector["padham_substring_signals"]
    )
    detector["stats"]["meaning_keyword_count"] = len(detector["meaning_keywords"])
    return detector


def validate_detector_against_pasurams(
    records: List[Dict[str, Any]],
    detector: Dict[str, Any],
) -> Dict[str, Any]:
    prepared = prepare_detector(detector)
    pasurams = sorted({r.get("PasuramNumber") for r in records if r.get("PasuramNumber") is not None})

    would_trigger: Set[Any] = set()
    for pasuram_num in pasurams:
        subset = [r for r in records if r.get("PasuramNumber") == pasuram_num]
        for row in subset:
            padham = str(row.get("Padham", "")).strip()
            if not padham or padham.upper() == "NOTE":
                continue
            matched, _, _ = line_triggers_theme(padham, str(row.get("Meaning", "")), prepared)
            if matched:
                would_trigger.add(pasuram_num)
                break

    result: Dict[str, Any] = {
        "pasurams_in_source": len(pasurams),
        "pasurams_detector_would_trigger": len(would_trigger),
        "pasurams_missed": sorted(set(pasurams) - would_trigger)[:50],
    }
    if detector.get("theme_id") == "mahabharatham":
        result["pasuram_80_triggers"] = 80 in would_trigger
    return result


def build_theme(
    theme_id: str,
    db_config: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, Any]:
    theme_config = get_theme(theme_id)
    query_concepts = theme_config.get("query_concepts", [theme_config.get("concept", theme_id)])

    print(f"Loading {theme_id}-tagged rows from `{db_config['table']}`...")
    raw_rows = query_concept_rows(db_config, query_concepts)
    records: List[Dict[str, Any]] = []
    for row in raw_rows:
        built = build_record(row)
        if built:
            records.append(built)

    if not records:
        print(f"  WARNING: no tagged rows found for theme {theme_id}")

    detector = build_detector_from_records(
        records,
        theme_id=theme_id,
        theme_config=theme_config,
        source_table=db_config["table"],
    )
    validation = validate_detector_against_pasurams(records, detector)
    detector["validation"] = validation

    output_path = detector_path_for_theme(theme_id, output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(detector, fh, ensure_ascii=False, indent=2)

    print(f"Wrote {output_path}")
    print(f"  Tagged rows: {detector['stats']['tagged_rows_analyzed']}")
    print(f"  Strong signal lines: {detector['stats']['strong_signal_lines']}")
    print(f"  Weak (pasuram-only) lines: {detector['stats']['weak_pasuram_only_lines']}")
    print(
        f"  Pasurams detector triggers: "
        f"{validation['pasurams_detector_would_trigger']}/{validation['pasurams_in_source']}"
    )
    if validation.get("pasurams_missed"):
        print(f"  Sample missed pasurams: {validation['pasurams_missed'][:10]}")
    return detector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build theme detectors from POC SimilarWords tags")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--table", default=None)
    parser.add_argument(
        "--theme",
        default="all",
        help="Theme id or comma-separated list, or 'all' (default)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_DETECTORS_DIR),
        help="Directory for {theme}_detector.json files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_config = load_db_config(Path(args.config))
    if args.table:
        db_config["table"] = args.table

    registry = load_theme_registry()
    theme_ids = resolve_theme_ids(args.theme, registry)
    output_dir = Path(args.output_dir)

    for theme_id in theme_ids:
        if theme_id not in registry.get("themes", {}):
            raise KeyError(f"Unknown theme: {theme_id}")
        print(f"\n=== Building detector: {theme_id} ===")
        build_theme(theme_id, db_config, output_dir)


if __name__ == "__main__":
    main()
