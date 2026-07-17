#!/usr/bin/env python3
"""Scan an Excel workbook for pasurams that would receive theme SimilarWords tags."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from lookupsimilarwords.pasuram_themes import load_detectors_for_themes
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR, resolve_theme_ids
from lookupsimilarwords.workbook_scan import (
    build_combined_report,
    build_theme_report,
    excel_rows_to_groups,
    save_theme_csv_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan workbook for theme-taggable pasurams")
    parser.add_argument("--input", default="Thiruvandhathi2and3.xlsx")
    parser.add_argument("--sheet", default=None)
    parser.add_argument(
        "--theme",
        default="all",
        help="Theme id, comma-separated list, or 'all'",
    )
    parser.add_argument(
        "--detectors-dir",
        default=str(DEFAULT_DETECTORS_DIR),
    )
    parser.add_argument(
        "--output-dir",
        default="lookupsimilarwords",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Workbook not found: {input_path}")

    theme_ids = resolve_theme_ids(args.theme)
    detectors_dir = Path(args.detectors_dir)
    detectors = load_detectors_for_themes(theme_ids, detectors_dir)
    if not detectors:
        raise FileNotFoundError(
            f"No detectors found in {detectors_dir} for themes: {theme_ids}. "
            "Run build_theme_detector.py first."
        )

    df = pd.read_excel(input_path, sheet_name=args.sheet or 0)
    groups = excel_rows_to_groups(df)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanned {len(groups)} pasurams from {input_path}\n")

    for detector in detectors:
        theme_id = detector.get("theme_id", detector.get("concept", "theme"))
        detector_path = detectors_dir / f"{theme_id}_detector.json"
        report = build_theme_report(
            groups,
            detector,
            source_workbook=str(input_path),
            detector_file=str(detector_path),
        )
        json_path = out_dir / f"thiruvandhathi_{theme_id}_report.json"
        csv_path = out_dir / f"thiruvandhathi_{theme_id}_report.csv"
        with json_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        save_theme_csv_report(report, csv_path, theme_id=theme_id)

        print(f"=== {theme_id} ===")
        print(f"  Would tag {report['tagged_pasuram_count']} pasurams")
        print(f"  Numbers: {report['tagged_pasuram_numbers']}")
        print(f"  Wrote {json_path}")
        print(f"  Wrote {csv_path}\n")

    if len(detectors) > 1:
        combined = build_combined_report(groups, detectors, source_workbook=str(input_path))
        combined_path = out_dir / "thiruvandhathi_all_themes_report.json"
        with combined_path.open("w", encoding="utf-8") as fh:
            json.dump(combined, fh, ensure_ascii=False, indent=2)
        multi = [p for p in combined["pasurams"] if len(p["themes_triggered"]) > 1]
        print(f"=== Combined ===")
        print(f"  Multi-theme pasurams: {len(multi)}")
        if multi:
            for p in multi[:10]:
                print(f"    {p['pasuram_number']}: {p['themes_triggered']}")
        print(f"  Wrote {combined_path}")


if __name__ == "__main__":
    main()
