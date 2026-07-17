#!/usr/bin/env python3
"""Generate SimilarWords and finalize POC records."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_DETECTORS_DIR = (
    Path(__file__).resolve().parent.parent / "lookupsimilarwords" / "detectors"
)
DEFAULT_MB_DETECTOR = DEFAULT_DETECTORS_DIR / "mahabharatham_detector.json"
LEGACY_MB_DETECTOR = (
    Path(__file__).resolve().parent.parent / "lookupsimilarwords" / "mahabharatham_detector.json"
)


def make_similar_words(padham: str, transliteration: str, title: str) -> str:
    return f"{padham}, {transliteration}, {title}"


def _extract_transliteration(word_field: str) -> str:
    if not word_field:
        return ""
    parts = word_field.split(",", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return parts[0].strip()


def finalize_records(
    records: List[Dict],
    apply_themes: bool = True,
    apply_mahabharatham: Optional[bool] = None,
    themes: Optional[List[str]] = None,
    detectors_dir: Optional[Path] = None,
    detector_path: Optional[Path] = None,
    group_by_pasuram_number: bool = False,
) -> List[Dict]:
    finalized: List[Dict] = []
    for record in records:
        padham = record.get("Padham", "")
        word = record.get("Word", "")
        transliteration = _extract_transliteration(word)
        # Prabandham Tamil + English title goes in SimilarWords (not commentary Title field).
        title = record.get("PrabandhamTitle") or record.get("Title", "")
        similar = make_similar_words(padham, transliteration, title)
        row = {k: v for k, v in record.items() if k != "PrabandhamTitle"}
        finalized.append({**row, "SimilarWords": similar})

    if apply_mahabharatham is not None:
        apply_themes = apply_mahabharatham

    if not apply_themes:
        return finalized

    from lookupsimilarwords.pasuram_themes import (
        apply_all_themes_to_records,
        load_detectors_for_themes,
        load_theme_detector,
        pasuram_number_only_group_key,
    )

    base_dir = detectors_dir or DEFAULT_DETECTORS_DIR
    detectors = load_detectors_for_themes(themes, base_dir)

    if not detectors:
        fallback = detector_path or LEGACY_MB_DETECTOR
        if fallback.exists():
            detectors = [load_theme_detector(fallback)]

    if not detectors:
        return finalized

    group_key_fn = pasuram_number_only_group_key if group_by_pasuram_number else None
    return apply_all_themes_to_records(finalized, detectors, group_key_fn=group_key_fn)
