#!/usr/bin/env python3
"""Shared helpers for scanning Excel workbooks for theme-tagged pasurams."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from lookupsimilarwords.pasuram_themes import find_all_triggers_in_lines, normalize_text, prepare_detector


def _safe_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def excel_rows_to_groups(df: pd.DataFrame) -> Dict[int, List[Dict[str, Any]]]:
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for _, row in df.iterrows():
        pasuram_num = _safe_int(row.get("PasuramNumber"))
        if pasuram_num is None:
            continue
        padham = normalize_text(row.get("Padham", ""))
        if not padham or padham.upper() == "NOTE":
            continue
        groups.setdefault(pasuram_num, []).append(
            {
                "PasuramNumber": pasuram_num,
                "PattuNumber": _safe_int(row.get("PattuNumber")),
                "PadhamNumber": _safe_int(row.get("PadhamNumber")),
                "Padham": padham,
                "Meaning": normalize_text(row.get("Meaning", "")),
                "Word": normalize_text(row.get("Word", "")),
                "Prabandham": normalize_text(row.get("Prabandham", "")),
                "Title": normalize_text(row.get("Title", "")),
            }
        )
    return groups


def build_theme_report(
    groups: Dict[int, List[Dict[str, Any]]],
    detector: Dict[str, Any],
    source_workbook: str,
    detector_file: str = "",
) -> Dict[str, Any]:
    prepared = prepare_detector(detector)
    theme_id = detector.get("theme_id", detector.get("concept", "theme"))
    pasuram_summaries: List[Dict[str, Any]] = []
    triggered_numbers: List[int] = []

    for pasuram_num in sorted(groups.keys()):
        lines = groups[pasuram_num]
        trigger_lines = find_all_triggers_in_lines(lines, prepared)
        would_tag = len(trigger_lines) > 0
        first = trigger_lines[0] if trigger_lines else {}

        entry = {
            "pasuram_number": pasuram_num,
            "theme_id": theme_id,
            "would_tag": would_tag,
            "trigger_padham": first.get("padham"),
            "trigger_meaning_snippet": first.get("meaning_snippet"),
            "trigger_reason": first.get("reason"),
            "trigger_matched_term": first.get("matched_term"),
            "trigger_padhams": [t["padham"] for t in trigger_lines],
            "trigger_lines": trigger_lines,
            "line_count": len(lines),
            "prabandham": lines[0].get("Prabandham", "") if lines else "",
            "lines": lines,
        }
        pasuram_summaries.append(entry)
        if would_tag:
            triggered_numbers.append(pasuram_num)

    return {
        "theme_id": theme_id,
        "concept": detector.get("concept", theme_id),
        "aliases": detector.get("aliases", []),
        "source_workbook": source_workbook,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "detector_file": detector_file,
        "pasuram_count": len(groups),
        "tagged_pasuram_count": len(triggered_numbers),
        "tagged_pasuram_numbers": triggered_numbers,
        "pasurams": pasuram_summaries,
    }


def save_theme_csv_report(report: Dict[str, Any], csv_path: Path, theme_id: str = "") -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    theme_id = theme_id or report.get("theme_id", "theme")
    fieldnames = [
        "pasuram_number",
        "theme_id",
        "would_tag",
        "trigger_padham",
        "all_trigger_padhams",
        "trigger_reason",
        "trigger_matched_term",
        "trigger_meaning_snippet",
        "line_count",
        "prabandham",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for pasuram in report["pasurams"]:
            if pasuram["would_tag"]:
                for trigger in pasuram.get("trigger_lines", []):
                    writer.writerow(
                        {
                            "pasuram_number": pasuram["pasuram_number"],
                            "theme_id": theme_id,
                            "would_tag": True,
                            "trigger_padham": trigger["padham"],
                            "all_trigger_padhams": "; ".join(pasuram.get("trigger_padhams", [])),
                            "trigger_reason": trigger["reason"],
                            "trigger_matched_term": trigger.get("matched_term"),
                            "trigger_meaning_snippet": trigger.get("meaning_snippet")
                            or trigger.get("meaning", "")[:120],
                            "line_count": pasuram["line_count"],
                            "prabandham": pasuram["prabandham"],
                        }
                    )
            else:
                writer.writerow(
                    {
                        "pasuram_number": pasuram["pasuram_number"],
                        "theme_id": theme_id,
                        "would_tag": False,
                        "trigger_padham": "",
                        "all_trigger_padhams": "",
                        "trigger_reason": "",
                        "trigger_matched_term": "",
                        "trigger_meaning_snippet": "",
                        "line_count": pasuram["line_count"],
                        "prabandham": pasuram["prabandham"],
                    }
                )


def build_combined_report(
    groups: Dict[int, List[Dict[str, Any]]],
    detectors: List[Dict[str, Any]],
    source_workbook: str,
) -> Dict[str, Any]:
    theme_reports: List[Dict[str, Any]] = []
    pasuram_themes: Dict[int, List[str]] = {}

    for detector in detectors:
        prepared = prepare_detector(detector)
        theme_id = detector.get("theme_id", detector.get("concept", "theme"))
        for pasuram_num, lines in groups.items():
            trigger_lines = find_all_triggers_in_lines(lines, prepared)
            if trigger_lines:
                pasuram_themes.setdefault(pasuram_num, []).append(theme_id)

    combined_pasurams: List[Dict[str, Any]] = []
    for pasuram_num in sorted(groups.keys()):
        themes = pasuram_themes.get(pasuram_num, [])
        combined_pasurams.append(
            {
                "pasuram_number": pasuram_num,
                "themes_triggered": themes,
                "line_count": len(groups[pasuram_num]),
                "prabandham": groups[pasuram_num][0].get("Prabandham", "") if groups[pasuram_num] else "",
            }
        )

    return {
        "source_workbook": source_workbook,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "pasuram_count": len(groups),
        "multi_theme_pasuram_count": sum(1 for p in combined_pasurams if len(p["themes_triggered"]) > 1),
        "pasurams_with_themes": [p for p in combined_pasurams if p["themes_triggered"]],
        "pasurams": combined_pasurams,
        "theme_reports": theme_reports,
    }
