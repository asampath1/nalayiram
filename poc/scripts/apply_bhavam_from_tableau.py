#!/usr/bin/env python3
"""Match Tableau Pasuram-Nu to POC PasuramNumber and tag SimilarWords.

Never infers bhavam from Padham. Reads poc/data/bhavam_tableau.csv.
POC table only. Default is dry-run. Skip Male. Skip PasuramNumber 0.

  poc/.venv/bin/python poc/scripts/apply_bhavam_from_tableau.py --dry-run
  poc/.venv/bin/python poc/scripts/apply_bhavam_from_tableau.py --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lookupsimilarwords.pasuram_themes import append_theme_aliases, normalize_text
from poc.config import load_config
from poc.scripts.bhavam_common import (
    SKIP_ROLES,
    TABLEAU_CSV,
    aliases_for_role,
    normalize_role,
    prabandham_ta,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply Tableau bhavam tags to POC (PasuramNumber match)")
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--csv", default=str(TABLEAU_CSV))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"CSV missing: {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip() for f in (reader.fieldnames or [])]
        if "pasuram_number" not in fields or "bhavam" not in fields:
            raise SystemExit("CSV must have pasuram_number and bhavam columns")
        rows = []
        for raw in reader:
            pn_s = (raw.get("pasuram_number") or "").strip()
            role = normalize_role(raw.get("bhavam") or "")
            if not pn_s:
                continue
            try:
                pn = int(pn_s)
            except ValueError:
                continue
            if pn <= 0:
                continue
            if role in SKIP_ROLES or role.lower() == "male":
                continue
            if role not in ("Mother", "Nayaki", "Thozhi"):
                continue
            rows.append(
                {
                    "pasuram_number": pn,
                    "bhavam": role,
                    "prabandham_en": (raw.get("prabandham_en") or "").strip(),
                    "notation": (raw.get("notation") or "").strip(),
                    "pasuram_text": (raw.get("pasuram_text") or "").strip(),
                }
            )
    return rows


def fetch_db_verses(conn, table: str, numbers: List[int]) -> Dict[int, Dict[str, Any]]:
    if not numbers:
        return {}
    cur = conn.cursor(dictionary=True)
    found: Dict[int, Dict[str, Any]] = {}
    chunk = 400
    for i in range(0, len(numbers), chunk):
        part = numbers[i : i + chunk]
        ph = ",".join(["%s"] * len(part))
        cur.execute(
            f"SELECT Sno, PasuramNumber, PadhamNumber, Prabandham, Pasuram, SimilarWords "
            f"FROM `{table}` WHERE PasuramNumber IN ({ph}) AND PasuramNumber <> 0 "
            f"ORDER BY PasuramNumber, PadhamNumber",
            part,
        )
        for row in cur.fetchall():
            pn = int(row["PasuramNumber"])
            bucket = found.setdefault(
                pn,
                {"prabandham": row.get("Prabandham") or "", "pasuram": row.get("Pasuram") or "", "rows": []},
            )
            bucket["rows"].append(row)
    cur.close()
    return found


def main() -> None:
    args = parse_args()
    dry_run = not args.apply
    if args.dry_run:
        dry_run = True

    csv_rows = load_csv(Path(args.csv))
    if not csv_rows:
        raise SystemExit(
            f"No Mother/Nayaki/Thozhi rows in {args.csv}. "
            "Fill Pasuram-Nu + bhavam from Tableau (skip Male)."
        )

    by_pn: Dict[int, str] = {}
    conflicts: List[Tuple[int, str, str]] = []
    for row in csv_rows:
        pn = row["pasuram_number"]
        role = row["bhavam"]
        if pn in by_pn and by_pn[pn] != role:
            conflicts.append((pn, by_pn[pn], role))
        else:
            by_pn[pn] = role

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
    try:
        db_verses = fetch_db_verses(conn, db.table, list(by_pn.keys()))
        missing = sorted(set(by_pn) - set(db_verses))
        prabandham_mismatch: List[Dict[str, Any]] = []
        updates: List[Tuple[int, str]] = []
        tagged_pasurams: Dict[str, Set[int]] = defaultdict(set)

        csv_by_pn = {r["pasuram_number"]: r for r in csv_rows}
        for pn, role in sorted(by_pn.items()):
            verse = db_verses.get(pn)
            if not verse:
                continue
            expected_ta = prabandham_ta(csv_by_pn[pn].get("prabandham_en") or "")
            got_ta = (verse.get("prabandham") or "").strip()
            if expected_ta and got_ta and expected_ta not in got_ta and got_ta not in expected_ta:
                prabandham_mismatch.append(
                    {"pasuram_number": pn, "tableau": expected_ta, "db": got_ta, "bhavam": role}
                )
                continue
            aliases = aliases_for_role(role)
            if not aliases:
                continue
            tagged_pasurams[role].add(pn)
            for prow in verse["rows"]:
                old_sw = prow.get("SimilarWords") or ""
                new_sw = append_theme_aliases(old_sw, aliases)
                if normalize_text(new_sw) != normalize_text(old_sw):
                    updates.append((int(prow["Sno"]), new_sw))

        summary = {
            "dry_run": dry_run,
            "csv_rows": len(csv_rows),
            "unique_pasurams": len(by_pn),
            "conflicts": conflicts,
            "missing_in_db": missing,
            "prabandham_mismatch": prabandham_mismatch[:20],
            "prabandham_mismatch_n": len(prabandham_mismatch),
            "pasurams_by_role": {k: len(v) for k, v in tagged_pasurams.items()},
            "rows_would_update": len(updates),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if conflicts:
            raise SystemExit("Conflicting bhavam for the same PasuramNumber; fix CSV.")
        if dry_run:
            print("Dry-run: no UPDATE. Use --apply to write SimilarWords on POC.")
            return
        cur = conn.cursor()
        for sno, new_sw in updates:
            cur.execute(f"UPDATE `{db.table}` SET SimilarWords = %s WHERE Sno = %s", (new_sw, sno))
        conn.commit()
        cur.close()
        print(f"Updated {len(updates)} POC rows.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
