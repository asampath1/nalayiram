#!/usr/bin/env python3
"""Apply pathigam search aliases to POC DB and release-note link source.

Adds `{code} {short_name}` (or `{n}-{short}` for நாச்சியார்/பெருமாள்)
to SimilarWords and rewrites padhamPrefix in release_notes_link_source.html.

  poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --dry-run
  poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --apply
  poc/.venv/bin/python poc/scripts/apply_pathigam_search_aliases.py --apply --rebuild-release-notes
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config
from poc.scripts.pathigam_search_aliases import (
    GROUP_PRABANDHAM,
    SOURCE_HTML,
    aliases_by_pasuram,
    build_pathigam_catalog,
    merge_aliases,
    rewrite_link_source,
)


def apply_to_db(
    by_key: dict[tuple[str, int], list[str]],
    config_path: Path,
) -> int:
    config = load_config(str(config_path))
    db = config.database
    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cur = conn.cursor()
    updated = 0
    try:
        for (prabandham, pasuram_number), aliases in sorted(by_key.items()):
            cur.execute(
                f"SELECT SimilarWords FROM {db.table} "
                f"WHERE PasuramNumber=%s AND Prabandham=%s LIMIT 1",
                (pasuram_number, prabandham),
            )
            row = cur.fetchone()
            if not row:
                continue
            similar = merge_aliases(row[0] or "", aliases)
            cur.execute(
                f"UPDATE {db.table} SET SimilarWords=%s "
                f"WHERE PasuramNumber=%s AND Prabandham=%s",
                (similar, pasuram_number, prabandham),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return updated


def apply_to_json_files(by_key: dict[tuple[str, int], list[str]]) -> int:
    updated = 0
    for json_path in sorted((ROOT / "poc" / "output").glob("*_poc.json")):
        records = json.loads(json_path.read_text(encoding="utf-8"))
        changed = False
        for row in records:
            prabandham = str(row.get("Prabandham") or "")
            pasuram_number = int(row["PasuramNumber"])
            aliases = by_key.get((prabandham, pasuram_number))
            if not aliases:
                continue
            similar = merge_aliases(str(row.get("SimilarWords") or ""), aliases)
            if similar != row.get("SimilarWords"):
                row["SimilarWords"] = similar
                changed = True
                updated += 1
        if changed:
            json_path.write_text(
                json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return updated


def print_summary(catalog: dict) -> None:
    by_group: dict[str, list] = defaultdict(list)
    for spec in catalog.values():
        by_group[spec.group].append(spec)

    print(f"Pathigam catalog: {len(catalog)} pathigams\n")
    for group in GROUP_PRABANDHAM:
        items = by_group.get(group, [])
        if not items:
            continue
        print(f"## {GROUP_PRABANDHAM[group]} ({len(items)})")
        for spec in items[:3]:
            print(f"  {spec.alias} ({spec.start}-{spec.end})")
        if len(items) > 3:
            print(f"  ... +{len(items) - 3} more")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--source", default=str(SOURCE_HTML))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--rebuild-release-notes",
        action="store_true",
        help="Run build_newreleasenote_poc_v1.py --env poc after apply",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    source_html = source_path.read_text(encoding="utf-8")
    catalog = build_pathigam_catalog(source_html)
    by_key = aliases_by_pasuram(catalog.values())
    print_summary(catalog)
    print(f"Pasuram rows to touch: {len(by_key)}")

    if args.dry_run and not args.apply:
        print("Dry run — no DB / link-source changes.")
        return

    if not args.apply:
        print("Use --apply to update DB and link source.")
        return

    db_rows = apply_to_db(by_key, Path(args.config))
    json_rows = apply_to_json_files(by_key)

    new_html = rewrite_link_source(source_html, catalog)
    source_path.write_text(new_html, encoding="utf-8")
    print(f"Updated {source_path}")
    print(f"DB rows updated: {db_rows}; JSON rows updated: {json_rows}")

    if args.rebuild_release_notes:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "poc/scripts/build_newreleasenote_poc_v1.py"),
                "--env",
                "poc",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
