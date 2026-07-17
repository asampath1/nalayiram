#!/usr/bin/env python3
"""Mine Padham/Meaning signals from POC training rows (SimilarWords-tagged), then scan full table.

Training rows: any row where SimilarWords matches theme query_concepts (your ~28K corpus
of manually enriched aliases). Full scan: every padham line checked with the detector;
reports pasurams that would receive alias concatenation (non-FP per registry guards).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.config import load_db_config
from lookupsimilarwords.extract_concept_lookup import build_record, normalize_text, query_concept_rows
from lookupsimilarwords.pasuram_themes import (
    find_all_triggers_in_lines,
    line_triggers_theme,
    load_theme_detector,
    prepare_detector,
)
from lookupsimilarwords.theme_registry import (
    DEFAULT_DETECTORS_DIR,
    detector_path_for_theme,
    get_theme,
)


def _mine_stems_from_training(records: List[Dict[str, Any]], min_len: int = 4) -> Dict[str, Any]:
    """Frequency of substrings in Padham/Meaning on training rows (for seed vetting)."""
    meaning_counter: Counter = Counter()
    padham_counter: Counter = Counter()
    padham_exact: Counter = Counter()

    review_stems = [
        "நரசிம்", "நரசிங்", "narasim", "narsim", "இரணிய", "hiranya", "ஹிரண்ய",
        "ப்ரஹ்லாத", "பிரஹ்லாத", "அரி உருவ", "அரி ஆய்", "சிங்கம்",
    ]

    for rec in records:
        padham = normalize_text(rec.get("Padham", ""))
        meaning = normalize_text(rec.get("Meaning", ""))
        if padham:
            padham_exact[padham] += 1
        for stem in review_stems:
            if stem.lower() in meaning.lower():
                meaning_counter[stem] += 1
            if stem.lower() in padham.lower():
                padham_counter[stem] += 1

    return {
        "training_row_count": len(records),
        "training_pasuram_count": len({r.get("PasuramNumber") for r in records}),
        "top_padham_lines": padham_exact.most_common(40),
        "meaning_stem_hits": meaning_counter.most_common(30),
        "padham_stem_hits": padham_counter.most_common(30),
    }


def _scan_full_table(
    db_config: Dict[str, Any],
    prepared: Dict[str, Any],
    batch_size: int = 5000,
) -> Tuple[List[Dict[str, Any]], int]:
    import mysql.connector

    ssl_options = {} if not db_config.get("use_ssl") else {"ssl_disabled": False}
    conn = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        **ssl_options,
    )
    table = db_config["table"]
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"SELECT PasuramNumber, PattuNumber, PadhamNumber, Padham, Meaning, Prabandham, SimilarWords "
        f"FROM `{table}` "
        f"WHERE Padham IS NOT NULL AND TRIM(Padham) != '' AND UPPER(TRIM(Padham)) != 'NOTE' "
        f"ORDER BY PasuramNumber, PadhamNumber"
    )

    by_pasuram: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    total_rows = 0
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            total_rows += 1
            rec = build_record(row)
            if rec:
                by_pasuram[rec["PasuramNumber"]].append(rec)

    cursor.close()
    conn.close()

    summaries: List[Dict[str, Any]] = []
    for pasuram_num in sorted(by_pasuram.keys(), key=lambda x: (isinstance(x, str), x)):
        lines = by_pasuram[pasuram_num]
        triggers = find_all_triggers_in_lines(lines, prepared)
        if not triggers:
            continue
        prabandham = lines[0].get("Prabandham", "") if lines else ""
        summaries.append(
            {
                "pasuram_number": pasuram_num,
                "prabandham": prabandham,
                "line_count": len(lines),
                "trigger_count": len(triggers),
                "triggers": triggers[:8],
            }
        )

    return summaries, total_rows


def _known_fp_pasurams() -> Set[int]:
    """Golden non-Narasimha (அரிய etc.)."""
    return {2202, 2226, 2231, 2362}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train from SimilarWords tags, scan full POC Padham/Meaning")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--theme", default="narasimha")
    parser.add_argument("--detector", default=None)
    parser.add_argument("--output-dir", default="lookupsimilarwords/reviews")
    args = parser.parse_args()

    theme_id = args.theme
    theme_config = get_theme(theme_id)
    db_config = load_db_config(Path(args.config))
    detector_path = Path(args.detector) if args.detector else detector_path_for_theme(theme_id)
    if not detector_path.exists():
        raise FileNotFoundError(f"Detector not found: {detector_path}. Run build_theme_detector.py first.")

    query_concepts = theme_config.get("query_concepts", [])
    print(f"=== Training extract: SimilarWords contains {query_concepts} ===")
    raw_rows = query_concept_rows(db_config, query_concepts)
    training_records: List[Dict[str, Any]] = []
    for row in raw_rows:
        built = build_record(row)
        if built:
            training_records.append(built)

    mined = _mine_stems_from_training(training_records)
    print(f"  Training rows: {mined['training_row_count']}")
    print(f"  Training pasurams: {mined['training_pasuram_count']}")

    prepared = prepare_detector(load_theme_detector(detector_path))
    print(f"\n=== Full POC scan: Padham + Meaning (table {db_config['table']}) ===")
    pasuram_summaries, total_rows = _scan_full_table(db_config, prepared)
    print(f"  Total padham rows scanned: {total_rows}")
    print(f"  Pasurams detector would tag: {len(pasuram_summaries)}")

    thiru = [p for p in pasuram_summaries if 2182 <= int(p["pasuram_number"]) <= 2381]
    outside = [p for p in pasuram_summaries if not (2182 <= int(p["pasuram_number"]) <= 2381)]
    fp_candidates = [p for p in pasuram_summaries if int(p["pasuram_number"]) in _known_fp_pasurams()]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "theme_id": theme_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_table": db_config["table"],
        "aliases_appended_on_trigger": theme_config.get("aliases", []),
        "training_from_similar_words": mined,
        "full_scan": {
            "total_padham_rows": total_rows,
            "pasurams_would_tag": len(pasuram_summaries),
            "thiruvandhathi_2182_2381_count": len(thiru),
            "outside_thiruvandhathi_count": len(outside),
        },
        "pasurams_would_tag": pasuram_summaries,
        "thiruvandhathi_pasurams": [p["pasuram_number"] for p in thiru],
        "outside_thiruvandhathi_sample": [p["pasuram_number"] for p in outside[:30]],
        "fp_watchlist": [p["pasuram_number"] for p in fp_candidates],
    }

    json_path = out_dir / f"{theme_id}_poc_full_scan.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    csv_path = out_dir / f"{theme_id}_poc_full_scan.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["pasuram_number", "prabandham", "line_count", "trigger_count", "sample_padham", "sample_term"],
        )
        writer.writeheader()
        for p in pasuram_summaries:
            tr = p["triggers"][0] if p["triggers"] else {}
            writer.writerow(
                {
                    "pasuram_number": p["pasuram_number"],
                    "prabandham": p["prabandham"],
                    "line_count": p["line_count"],
                    "trigger_count": p["trigger_count"],
                    "sample_padham": (tr.get("padham") or "")[:60],
                    "sample_term": tr.get("matched_term") or "",
                }
            )

    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
