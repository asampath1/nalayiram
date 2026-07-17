#!/usr/bin/env python3
"""Pasuram-level theme tagging: detect signals on any line, tag all rows in that pasuram."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from lookupsimilarwords.theme_registry import (
    DEFAULT_DETECTORS_DIR,
    detector_path_for_theme,
    list_theme_ids,
    load_theme_registry,
    resolve_theme_ids,
)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", str(text or ""))
    text = re.sub(r"[\s\u00A0]+", " ", text).strip()
    return text


def normalize_meaning_for_mb(meaning: str) -> str:
    """Unwrap parenthetical Tamil glosses so e.g. (பாரத) யுத்த matches பாரத யுத்த."""
    return normalize_meaning_for_theme(meaning, unwrap_parenthesis=True)


def normalize_meaning_for_theme(meaning: str, unwrap_parenthesis: bool = False) -> str:
    text = normalize_text(meaning)
    if unwrap_parenthesis:
        text = re.sub(r"\(\s*([^()]+)\s*\)", r" \1 ", text)
        text = re.sub(r"[\s\u00A0]+", " ", text).strip()
    return text


def load_theme_detector(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_mahabharatham_detector(path: Path) -> Dict[str, Any]:
    return load_theme_detector(path)


def load_detectors_for_themes(
    theme_ids: Optional[List[str]] = None,
    detectors_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    ids = theme_ids or list_theme_ids()
    base = detectors_dir or DEFAULT_DETECTORS_DIR
    detectors: List[Dict[str, Any]] = []
    for theme_id in ids:
        path = detector_path_for_theme(theme_id, base)
        if not path.exists():
            legacy = Path(__file__).resolve().parent / f"{theme_id}_detector.json"
            if theme_id == "mahabharatham":
                legacy = Path(__file__).resolve().parent / "mahabharatham_detector.json"
            path = legacy if legacy.exists() else path
        if path.exists():
            detector = load_theme_detector(path)
            detector.setdefault("theme_id", theme_id)
            detectors.append(detector)
    return detectors


def _compile_patterns(terms: List[str]) -> List[re.Pattern]:
    patterns: List[re.Pattern] = []
    for term in terms:
        term = normalize_text(term)
        if not term:
            continue
        patterns.append(re.compile(re.escape(term), re.IGNORECASE))
    return patterns


def _compile_blocked_context_patterns(
    rules: List[Dict[str, Any]],
) -> List[Tuple[str, re.Pattern, bool]]:
    compiled: List[Tuple[str, re.Pattern, bool]] = []
    for rule in rules:
        stem = normalize_text(rule.get("stem", ""))
        if not stem:
            continue
        needle = rule.get("if_text_matches") or rule.get("pattern", "")
        needle = normalize_text(needle)
        if not needle:
            continue
        prefix_match = bool(rule.get("prefix_match"))
        compiled.append(
            (
                stem.lower(),
                re.compile(re.escape(needle), re.IGNORECASE),
                prefix_match,
            )
        )
    return compiled


def _term_match_allowed(
    text: str,
    term: str,
    field: str,
    detector: Dict[str, Any],
) -> bool:
    """Reject substring hits that are known false positives for this theme."""
    term_n = normalize_text(term)
    if not term_n:
        return False

    text_n = normalize_text(text)

    min_len = detector.get("min_stem_length")
    if min_len is not None and len(term_n) < int(min_len):
        return False

    if field == "meaning":
        excluded = detector.get("meaning_only_excluded_stems") or []
        excluded_lower = {normalize_text(e).lower() for e in excluded if e}
        if term_n.lower() in excluded_lower:
            return False

    blocked = detector.get("_blocked_context_patterns")
    if blocked is None:
        blocked = _compile_blocked_context_patterns(detector.get("blocked_contexts") or [])
    term_lower = term_n.lower()
    for stem_lower, pattern, prefix_match in blocked:
        if prefix_match:
            if not term_lower.startswith(stem_lower):
                continue
        elif stem_lower != term_lower:
            continue
        if pattern.search(text_n):
            return False

    return True


def prepare_detector(detector: Dict[str, Any]) -> Dict[str, Any]:
    """Attach compiled patterns for repeated matching."""
    prepared = dict(detector)
    prepared["_meaning_patterns"] = _compile_patterns(detector.get("meaning_keywords", []))
    prepared["_padham_substring_patterns"] = _compile_patterns(
        detector.get("padham_substring_signals", [])
    )
    prepared["_blocked_context_patterns"] = _compile_blocked_context_patterns(
        detector.get("blocked_contexts") or []
    )
    return prepared


def line_triggers_theme(
    padham: str,
    meaning: str,
    detector: Dict[str, Any],
    pasuram: str = "",
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Return (matched, reason, matched_term) for a single padham line."""
    padham = normalize_text(padham)
    unwrap = bool(detector.get("normalize_meaning_parenthesis", False))
    meaning = normalize_meaning_for_theme(meaning, unwrap_parenthesis=unwrap)
    pasuram = normalize_text(pasuram)

    padham_patterns = detector.get("_padham_substring_patterns")
    if padham_patterns is None:
        padham_patterns = _compile_patterns(detector.get("padham_substring_signals", []))
    for pattern in padham_patterns:
        match = pattern.search(padham)
        if match and _term_match_allowed(padham, match.group(0), "padham", detector):
            return True, "padham_substring", match.group(0)

    meaning_patterns = detector.get("_meaning_patterns")
    if meaning_patterns is None:
        meaning_patterns = _compile_patterns(detector.get("meaning_keywords", []))
    for pattern in meaning_patterns:
        match = pattern.search(meaning)
        if match and _term_match_allowed(meaning, match.group(0), "meaning", detector):
            return True, "meaning_keyword", match.group(0)

    if pasuram:
        for pattern in padham_patterns:
            match = pattern.search(pasuram)
            if match and _term_match_allowed(pasuram, match.group(0), "padham", detector):
                return True, "pasuram_substring", match.group(0)
        for pattern in meaning_patterns:
            match = pattern.search(pasuram)
            if match and _term_match_allowed(pasuram, match.group(0), "meaning", detector):
                return True, "pasuram_keyword", match.group(0)

    return False, None, None


def line_triggers_mahabharatham(
    padham: str,
    meaning: str,
    detector: Dict[str, Any],
) -> Tuple[bool, Optional[str], Optional[str]]:
    return line_triggers_theme(padham, meaning, detector)


def find_all_triggers_in_lines(
    lines: List[Dict[str, Any]],
    prepared_detector: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return every padham line in a pasuram that matches the detector."""
    triggers: List[Dict[str, Any]] = []
    for line in lines:
        matched, reason, matched_term = line_triggers_theme(
            line["Padham"],
            line["Meaning"],
            prepared_detector,
        )
        if matched:
            triggers.append(
                {
                    "padham": line["Padham"],
                    "meaning": line["Meaning"],
                    "meaning_snippet": (line["Meaning"][:120] if line["Meaning"] else ""),
                    "reason": reason,
                    "matched_term": matched_term,
                }
            )
    return triggers


def find_all_mb_triggers_in_lines(
    lines: List[Dict[str, Any]],
    prepared_detector: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return find_all_triggers_in_lines(lines, prepared_detector)


def pasuram_group_key(record: Dict[str, Any]) -> Tuple[Any, Any]:
    return (record.get("PasuramNumber"), record.get("PattuNumber"))


def _pasuram_has_theme_trigger(
    indices: List[int],
    records: List[Dict[str, Any]],
    prepared: Dict[str, Any],
) -> bool:
    for idx in indices:
        record = records[idx]
        padham = str(record.get("Padham", "")).strip()
        if not padham or padham.upper() == "NOTE":
            continue
        matched, _, _ = line_triggers_theme(
            padham,
            str(record.get("Meaning", "")),
            prepared,
            pasuram=str(record.get("Pasuram", "")),
        )
        if matched:
            return True
    return False


def apply_theme_to_records(
    records: List[Dict[str, Any]],
    detector: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """If any line in a pasuram matches the detector, append theme aliases to every row."""
    prepared = prepare_detector(detector)
    aliases = detector.get("aliases", [])

    groups: Dict[Tuple[Any, Any], List[int]] = {}
    for idx, record in enumerate(records):
        key = pasuram_group_key(record)
        groups.setdefault(key, []).append(idx)

    triggered_keys: Set[Tuple[Any, Any]] = set()
    for key, indices in groups.items():
        if _pasuram_has_theme_trigger(indices, records, prepared):
            triggered_keys.add(key)

    result: List[Dict[str, Any]] = []
    for idx, record in enumerate(records):
        row = dict(record)
        key = pasuram_group_key(record)
        if key in triggered_keys:
            row["SimilarWords"] = append_theme_aliases(row.get("SimilarWords", ""), aliases)
        result.append(row)

    return result


def apply_mahabharatham_to_records(
    records: List[Dict[str, Any]],
    detector: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return apply_theme_to_records(records, detector)


def apply_all_themes_to_records(
    records: List[Dict[str, Any]],
    detectors: List[Dict[str, Any]],
    *,
    group_key_fn=None,
) -> List[Dict[str, Any]]:
    """Evaluate each theme independently; union all triggered aliases per pasuram."""
    if not detectors:
        return records

    key_fn = group_key_fn or pasuram_group_key
    prepared_list = [(prepare_detector(d), d.get("aliases", [])) for d in detectors]

    groups: Dict[Tuple[Any, ...], List[int]] = {}
    for idx, record in enumerate(records):
        key = key_fn(record)
        groups.setdefault(key, []).append(idx)

    pasuram_aliases: Dict[Tuple[Any, ...], List[str]] = {}
    for key, indices in groups.items():
        aliases_to_add: List[str] = []
        for prepared, aliases in prepared_list:
            if _pasuram_has_theme_trigger(indices, records, prepared):
                aliases_to_add.extend(aliases)
        if aliases_to_add:
            pasuram_aliases[key] = aliases_to_add

    result: List[Dict[str, Any]] = []
    for idx, record in enumerate(records):
        row = dict(record)
        key = key_fn(record)
        if key in pasuram_aliases:
            row["SimilarWords"] = append_theme_aliases(
                row.get("SimilarWords", ""),
                pasuram_aliases[key],
            )
        result.append(row)

    return result


def pasuram_number_only_group_key(record: Dict[str, Any]) -> Tuple[Any]:
    """Group all virtual pattus under one PasuramNumber (e.g. திருவெழுகூற்றிருக்கை 2672)."""
    return (record.get("PasuramNumber"),)


def append_theme_aliases(similar_words: str, aliases: List[str]) -> str:
    base = normalize_text(similar_words)
    parts = [p.strip() for p in re.split(r"[,;]+", base) if p.strip()] if base else []
    existing_lower = {p.lower() for p in parts}
    for alias in aliases:
        alias = normalize_text(alias)
        if alias and alias.lower() not in existing_lower:
            parts.append(alias)
            existing_lower.add(alias.lower())
    return ", ".join(parts)
