#!/usr/bin/env python3
"""Validate theme detectors against POC-tagged pasurams and optional Excel workbook."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.extract_concept_lookup import build_record, query_concept_rows
from lookupsimilarwords.pasuram_themes import find_all_triggers_in_lines, load_detectors_for_themes, prepare_detector
from lookupsimilarwords.theme_registry import DEFAULT_DETECTORS_DIR, get_theme, resolve_theme_ids
from lookupsimilarwords.workbook_scan import build_theme_report, excel_rows_to_groups, save_theme_csv_report


def poc_trigger_details(
    records: List[Dict[str, Any]],
    prepared: Dict[str, Any],
    theme_id: str,
) -> List[Dict[str, Any]]:
    pasurams = sorted({r.get("PasuramNumber") for r in records if r.get("PasuramNumber") is not None})
    details: List[Dict[str, Any]] = []
    for pasuram_num in pasurams:
        subset = [r for r in records if r.get("PasuramNumber") == pasuram_num]
        trigger_lines = find_all_triggers_in_lines(subset, prepared)
        triggered = len(trigger_lines) > 0
        trigger_info: Dict[str, Any] = {}
        if trigger_lines:
            trigger_info = {
                "trigger_padhams": [t["padham"] for t in trigger_lines],
                "trigger_lines": trigger_lines,
            }
        details.append(
            {
                "pasuram_number": pasuram_num,
                "theme_id": theme_id,
                "detector_would_tag": triggered,
                "manually_tagged": True,
                **trigger_info,
            }
        )
    return details


def validate_theme(
    theme_id: str,
    detector: Dict[str, Any],
    db_config: Dict[str, Any],
    out_dir: Path,
    workbook_path: Path,
) -> Dict[str, Any]:
    theme_config = get_theme(theme_id)
    query_concepts = theme_config.get("query_concepts", [theme_config.get("concept", theme_id)])
    prepared = prepare_detector(detector)

    raw_rows = query_concept_rows(db_config, query_concepts)
    poc_records: List[Dict[str, Any]] = []
    for row in raw_rows:
        built = build_record(row)
        if built:
            poc_records.append(built)

    poc_details = poc_trigger_details(poc_records, prepared, theme_id)
    missed = [d for d in poc_details if not d["detector_would_tag"]]
    would_tag = [d for d in poc_details if d["detector_would_tag"]]

    poc_report = {
        "theme_id": theme_id,
        "source": db_config["table"],
        "manually_tagged_pasurams": len(poc_details),
        "detector_would_tag": len(would_tag),
        "detector_missed": len(missed),
        "missed_pasuram_numbers": [d["pasuram_number"] for d in missed],
        "pasurams": poc_details,
    }
    poc_json = out_dir / f"{theme_id}_validation_poc.json"
    with poc_json.open("w", encoding="utf-8") as fh:
        json.dump(poc_report, fh, ensure_ascii=False, indent=2)

    wb_summary: Dict[str, Any] = {}
    if workbook_path.exists():
        df = pd.read_excel(workbook_path)
        groups = excel_rows_to_groups(df)
        wb_report = build_theme_report(
            groups,
            detector,
            source_workbook=str(workbook_path),
            detector_file=str(out_dir / "detectors" / f"{theme_id}_detector.json"),
        )
        wb_json = out_dir / f"thiruvandhathi_{theme_id}_report.json"
        with wb_json.open("w", encoding="utf-8") as fh:
            json.dump(wb_report, fh, ensure_ascii=False, indent=2)
        save_theme_csv_report(wb_report, out_dir / f"thiruvandhathi_{theme_id}_report.csv", theme_id)
        wb_summary = {
            "pasuram_count": wb_report["pasuram_count"],
            "tagged_pasuram_count": wb_report["tagged_pasuram_count"],
            "tagged_pasuram_numbers": wb_report["tagged_pasuram_numbers"],
        }

    print(f"=== {theme_id} POC validation ===")
    print(f"  Manually tagged pasurams: {len(poc_details)}")
    print(f"  Detector would tag:       {len(would_tag)}")
    print(f"  Detector missed:          {len(missed)}")
    if missed:
        print(f"  Missed: {[d['pasuram_number'] for d in missed][:20]}")
    print(f"  Wrote {poc_json}")
    if wb_summary:
        print(f"  Workbook would tag: {wb_summary['tagged_pasuram_count']} pasurams")

    return {
        "theme_id": theme_id,
        "manually_tagged_pasurams": len(poc_details),
        "detector_would_tag": len(would_tag),
        "detector_missed": len(missed),
        "missed_pasuram_numbers": [d["pasuram_number"] for d in missed],
        "workbook": wb_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate theme detectors (POC + workbook)")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--theme", default="all")
    parser.add_argument("--detectors-dir", default=str(DEFAULT_DETECTORS_DIR))
    parser.add_argument("--workbook", default="Thiruvandhathi2and3.xlsx")
    parser.add_argument("--output-dir", default="lookupsimilarwords")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    theme_ids = resolve_theme_ids(args.theme)
    detectors_dir = Path(args.detectors_dir)
    detectors = load_detectors_for_themes(theme_ids, detectors_dir)
    if not detectors:
        raise FileNotFoundError(f"No detectors found for themes: {theme_ids}")

    db_config = load_db_config(Path(args.config))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = Path(args.workbook)

    summaries: List[Dict[str, Any]] = []
    for detector in detectors:
        theme_id = detector.get("theme_id", detector.get("concept"))
        print()
        summary = validate_theme(theme_id, detector, db_config, out_dir, workbook_path)
        summaries.append(summary)

    summary_path = out_dir / "all_themes_validation_summary.json"
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump({"themes": summaries}, fh, ensure_ascii=False, indent=2)
    print(f"\nWrote summary: {summary_path}")


if __name__ == "__main__":
    main()
