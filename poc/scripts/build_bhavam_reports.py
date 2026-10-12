#!/usr/bin/env python3
"""Build POC bhavam report JSON (read-only SELECT). Does not tag verses.

Compares Tableau CSV (if filled) and existing SimilarWords aliases to chart compass.

  poc/.venv/bin/python poc/scripts/build_bhavam_reports.py --dry-run
  poc/.venv/bin/python poc/scripts/build_bhavam_reports.py --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.scripts.bhavam_common import (
    BHAVAM_ALIASES,
    COMPASS_JSON,
    OUT_JSON,
    TABLEAU_CSV,
    normalize_role,
)
from poc.scripts.build_padham_reports import EXCLUDED_PRABANDHAMS, canonical_alwar, nfc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build POC bhavam report JSON (read-only)")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_csv_tags(path: Path) -> Dict[str, Set[int]]:
    out: Dict[str, Set[int]] = {"Mother": set(), "Nayaki": set(), "Thozhi": set()}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            try:
                pn = int((raw.get("pasuram_number") or "").strip())
            except ValueError:
                continue
            if pn <= 0:
                continue
            role = normalize_role(raw.get("bhavam") or "")
            if role in out:
                out[role].add(pn)
    return out


def main() -> None:
    args = parse_args()
    compass = json.loads(COMPASS_JSON.read_text(encoding="utf-8"))
    csv_tags = load_csv_tags(TABLEAU_CSV)
    csv_n = sum(len(v) for v in csv_tags.values())

    config = load_config(args.config)
    db = config.database
    if db.table != "PasuramsArthamTablePOC":
        raise SystemExit(f"Refusing table {db.table!r}; expected PasuramsArthamTablePOC")

    import mysql.connector

    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"SELECT DISTINCT PasuramNumber, Alzwar, Prabandham, SimilarWords "
        f"FROM `{db.table}` WHERE PasuramNumber <> 0"
    )
    tagged: Dict[str, Dict[str, Set[int]]] = {
        role: defaultdict(set) for role in BHAVAM_ALIASES
    }
    tagged_total: Dict[str, Set[int]] = {role: set() for role in BHAVAM_ALIASES}
    try:
        for row in cur:
            pn = int(row["PasuramNumber"])
            pb = nfc(row.get("Prabandham"))
            if pb in EXCLUDED_PRABANDHAMS:
                continue
            similar = nfc(row.get("SimilarWords")).lower()
            alwar = canonical_alwar(row.get("Alzwar"))
            for role, aliases in BHAVAM_ALIASES.items():
                if any(a.lower() in similar for a in aliases):
                    tagged_total[role].add(pn)
                    tagged[role][pb].add(pn)
                    tagged[role][alwar].add(pn)
    finally:
        cur.close()
        conn.close()

    by_role = []
    for role in ("Mother", "Nayaki", "Thozhi"):
        compass_rows = compass.get("compass", {}).get(role, [])
        compass_total = sum(int(r.get("tableau_pasurams") or 0) for r in compass_rows)
        csv_count = len(csv_tags[role])
        db_count = len(tagged_total[role])
        compare = []
        for row in compass_rows:
            ta = row.get("prabandham_ta") or ""
            compare.append(
                {
                    "prabandham": ta,
                    "tableau_compass": int(row.get("tableau_pasurams") or 0),
                    "csv_pasurams": 0,
                    "db_tagged": len(tagged[role].get(ta, set())),
                }
            )
        by_role.append(
            {
                "role": role,
                "label_ta": BHAVAM_ALIASES[role][0],
                "search_alias": BHAVAM_ALIASES[role][0],
                "compass_total": compass_total,
                "csv_pasurams": csv_count,
                "db_tagged_pasurams": db_count,
                "prabandhams": compare,
            }
        )

    payload = {
        "meta": {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": compass.get("source"),
            "csv_path": str(TABLEAU_CSV.relative_to(ROOT)),
            "csv_pasurams": csv_n,
            "verse_list_ready": csv_n > 0,
            "method": "Tableau Pasuram-Nu matched to PasuramNumber. Not inferred from Padham.",
            "skip_roles": ["Male"],
        },
        "blocked": {
            "allow_export_data": False,
            "allow_view_underlying": False,
            "reason_ta": "Tableau அட்டவணையில் Data / Crosstab பதிவிறக்கம் அணைக்கப்பட்டுள்ளது. பாசுர எண் பட்டியலை CSV-ல் இடவும்.",
        },
        "roles": by_role,
    }

    print(json.dumps({k: payload["meta"] for k in ["meta"]}, ensure_ascii=False, indent=2))
    for block in by_role:
        print(
            f"{block['label_ta']}: compass {block['compass_total']} · "
            f"csv {block['csv_pasurams']} · DB {block['db_tagged_pasurams']}"
        )

    if args.dry_run and not args.apply:
        print("Dry-run: JSON not written.")
        return
    if not args.apply:
        print("Use --apply to write public_html/data/bhavam_reports_poc.json")
        return
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
