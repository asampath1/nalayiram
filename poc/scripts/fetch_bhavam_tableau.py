#!/usr/bin/env python3
"""Check Tableau Public bhavam dashboard and report whether verse rows can be fetched.

The author disabled Data / Crosstab / View Data. This script does not invent tags
from Padham. Drop a CSV at poc/data/bhavam_tableau.csv then run apply_bhavam_from_tableau.py.

  poc/.venv/bin/python poc/scripts/fetch_bhavam_tableau.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from poc.scripts.bhavam_common import COMPASS_JSON, TABLEAU_CSV


VIZ_URL = "https://public.tableau.com/views/sd_2/07-BhavamDashboard?:embed=y&:showVizHome=n"
APP_URL = "https://public.tableau.com/app/profile/ramanuja.dasargal/viz/sd_2/07-BhavamDashboard"


def csv_row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return max(0, len(lines) - 1)


def main() -> None:
    compass = json.loads(COMPASS_JSON.read_text(encoding="utf-8"))
    n_csv = csv_row_count(TABLEAU_CSV)
    print("Source:", APP_URL)
    print("Workbook:", compass.get("workbook"), "sheet:", compass.get("sheet"))
    print()
    print("Tableau Public guest session (checked 2026-09-02):")
    print("  allow_export_data = false")
    print("  allow_view_underlying = false")
    print("  Download menu = Image / PDF / PowerPoint only (no Data, no Crosstab)")
    print("  View Data window = not enabled")
    print("  Table is server-rendered (images), not HTML rows")
    print()
    print("Do not infer Mother / Nayaki / Thozhi from Padham or Title.")
    print("Acharya tags are verse-level: Pasuram-Nu + Azhwar-Gender-Role from the table")
    print("'05-Bhavams vs Pasurams'. Skip Male (not a nayaki-version bhavam).")
    print()
    print("CSV path:", TABLEAU_CSV.relative_to(ROOT))
    print("CSV data rows (excluding header):", n_csv)
    print("Required columns: pasuram_number,bhavam,prabandham_en,notation,pasuram_text")
    print("  bhavam = Mother | Nayaki | Thozhi")
    print("  pasuram_number = Tableau Pasuram-Nu (matches our PasuramNumber; e.g. 13 = பெரியாழ்வார் 1-1-1)")
    print()
    if n_csv == 0:
        print("Next: put the Tableau table into that CSV, then:")
        print("  poc/.venv/bin/python poc/scripts/apply_bhavam_from_tableau.py --dry-run")
        print("  poc/.venv/bin/python poc/scripts/apply_bhavam_from_tableau.py --apply")
        print("  poc/.venv/bin/python poc/scripts/build_bhavam_reports.py --apply")
        raise SystemExit(2)
    print("CSV has rows. Dry-run apply next.")


if __name__ == "__main__":
    main()
