#!/usr/bin/env python3
"""Scan an Excel workbook for pasurams that would receive Mahabharata SimilarWords tags."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.pasuram_themes import load_theme_detector
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR, detector_path_for_theme
from lookupsimilarwords.workbook_scan import build_theme_report, excel_rows_to_groups

DEFAULT_DETECTOR = detector_path_for_theme("mahabharatham", DEFAULT_DETECTORS_DIR)
LEGACY_DETECTOR = ROOT_DIR / "lookupsimilarwords" / "mahabharatham_detector.json"


def _load_mb_detector(path: Path):
    if path.exists():
        return load_theme_detector(path)
    if LEGACY_DETECTOR.exists():
        return load_theme_detector(LEGACY_DETECTOR)
    raise FileNotFoundError(f"MB detector not found: {path}")


def _to_legacy_report(report: dict) -> dict:
    legacy = dict(report)
    legacy["mb_pasuram_count"] = report.get("tagged_pasuram_count", 0)
    legacy["mb_pasuram_numbers"] = report.get("tagged_pasuram_numbers", [])
    for pasuram in legacy.get("pasurams", []):
        pasuram["would_tag_mb"] = pasuram.get("would_tag", False)
    return legacy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan workbook for MB-taggable pasurams")
    parser.add_argument("--input", default="Thiruvandhathi2and3.xlsx")
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--detector", default=str(DEFAULT_DETECTOR))
    parser.add_argument("--output-json", default="lookupsimilarwords/thiruvandhathi_mb_report.json")
    parser.add_argument("--output-csv", default="lookupsimilarwords/thiruvandhathi_mb_report.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Workbook not found: {input_path}")

    detector_path = Path(args.detector)
    detector = _load_mb_detector(detector_path)

    df = pd.read_excel(input_path, sheet_name=args.sheet or 0)
    groups = excel_rows_to_groups(df)
    report = build_theme_report(
        groups,
        detector,
        source_workbook=str(input_path),
        detector_file=str(detector_path if detector_path.exists() else LEGACY_DETECTOR),
    )
    legacy_report = _to_legacy_report(report)

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(legacy_report, fh, ensure_ascii=False, indent=2)

    csv_path = Path(args.output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    fieldnames = [
        "pasuram_number",
        "would_tag_mb",
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
                            "would_tag_mb": True,
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
                        "would_tag_mb": False,
                        "trigger_padham": "",
                        "all_trigger_padhams": "",
                        "trigger_reason": "",
                        "trigger_matched_term": "",
                        "trigger_meaning_snippet": "",
                        "line_count": pasuram["line_count"],
                        "prabandham": pasuram["prabandham"],
                    }
                )

    print(f"Scanned {report['pasuram_count']} pasurams from {input_path}")
    print(f"MB would tag {report['tagged_pasuram_count']} pasurams")
    print(f"Pasuram numbers: {report['tagged_pasuram_numbers']}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
