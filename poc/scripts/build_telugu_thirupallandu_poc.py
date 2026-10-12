#!/usr/bin/env python3
"""Build the Thirupallandu Telugu POC sandbox (clone + lipi + Meaning_te).

Does not write to PasuramsArthamTablePOC, pocindex.php, UAT, or Prod.

  poc/.venv/bin/python poc/scripts/build_telugu_thirupallandu_poc.py --dry-run
  poc/.venv/bin/python poc/scripts/build_telugu_thirupallandu_poc.py --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector
from openai import OpenAI

from poc.config import load_config
from poc.tamil_telugu_lipi import tamil_to_telugu_lipi, token_count_ok

PRABANDHAM = "திருப்பல்லாண்டு"
SOURCE_TABLE = "PasuramsArthamTablePOC"
ARTHAM_TE = "PasuramsArthamTableTeluguPOC"
DD_SOURCE = "DivyaDesamTable"
DD_TE = "DivyaDesamTableTeluguPOC"
CACHE_PATH = ROOT / "poc/cache/meaning_te_thirupallandu.json"
LIPI_CSV = ROOT / "poc/output/telugu_thirupallandu_lipi.csv"
MEANING_CSV = ROOT / "poc/output/telugu_thirupallandu_meaning_draft.csv"

ARTHAM_COPY_COLS = [
    "Sno",
    "Prabandham",
    "PasuramNumber",
    "Pasuram",
    "PattuNumber",
    "Word",
    "Meaning",
    "Alzwar",
    "PadhamNumber",
    "Padham",
    "SimilarWords",
    "Title",
    "NithyaanusandhamIndex",
]

TRANSLATE_SYSTEM = """You translate Tamil padhaartham (word-meaning glosses) into Telugu prose.

Rules:
- Translate the meaning only. Do not translate or rewrite any pasuram.
- Output ONLY the Telugu gloss. No labels, no quotes, no extra lines.
- If the input is empty, output UNSURE.
- Keep numbers. Render well-known names in Telugu letters (Periyalvar, Srirangam).
"""


def connect(config_path: Path):
    cfg = load_config(str(config_path))
    db = cfg.database
    return mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )


def source_counts(cur) -> tuple[int, int]:
    cur.execute(
        f"""
        SELECT COUNT(DISTINCT PasuramNumber), COUNT(*)
        FROM {SOURCE_TABLE}
        WHERE Prabandham = %s AND PasuramNumber BETWEEN 1 AND 12
        """,
        (PRABANDHAM,),
    )
    n_pasurams, n_rows = cur.fetchone()
    return int(n_pasurams), int(n_rows)


def load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def translate_meanings(meanings: list[str], cache: dict[str, str]) -> dict[str, str]:
    missing = [m for m in meanings if m not in cache]
    if not missing:
        return cache
    client = OpenAI()
    batch_size = 15
    for i in range(0, len(missing), batch_size):
        chunk = missing[i : i + batch_size]
        numbered = "\n".join(f"{idx+1}. {text}" for idx, text in enumerate(chunk))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "Translate each numbered Tamil meaning to Telugu. "
                        "Return the same number of lines, each starting with N. \n\n"
                        + numbered
                    ),
                },
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        parsed: list[str] = []
        for ln in lines:
            cleaned = re.sub(r"^[N]?(\d+)\.\s*", "", ln).strip()
            parsed.append(cleaned)
        if len(parsed) != len(chunk):
            # Fall back to one-at-a-time for this chunk.
            for text in chunk:
                one = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0,
                    messages=[
                        {"role": "system", "content": TRANSLATE_SYSTEM},
                        {"role": "user", "content": text},
                    ],
                )
                cache[text] = (one.choices[0].message.content or "").strip() or "UNSURE"
            continue
        for src, dest in zip(chunk, parsed):
            cache[src] = dest or "UNSURE"
        save_cache(cache)
        print(f"translated {min(i + batch_size, len(missing))}/{len(missing)} meanings")
    save_cache(cache)
    return cache


def create_tables(cur) -> None:
    cur.execute(f"DROP TABLE IF EXISTS {ARTHAM_TE}")
    cur.execute(f"DROP TABLE IF EXISTS {DD_TE}")
    cur.execute(f"CREATE TABLE {ARTHAM_TE} LIKE {SOURCE_TABLE}")
    cur.execute(f"CREATE TABLE {DD_TE} LIKE {DD_SOURCE}")
    for col, comment in (
        ("Pasuram_te", "Telugu lipi of Pasuram, not a translation"),
        ("Word_te", "Telugu lipi of Word, not a translation"),
        ("Meaning_te", "Telugu translation of Meaning only"),
    ):
        cur.execute(
            f"ALTER TABLE {ARTHAM_TE} ADD COLUMN {col} TEXT NULL COMMENT %s",
            (comment,),
        )


def copy_snapshot(cur) -> None:
    cols = ", ".join(ARTHAM_COPY_COLS)
    cur.execute(
        f"""
        INSERT INTO {ARTHAM_TE} ({cols})
        SELECT {cols}
        FROM {SOURCE_TABLE}
        WHERE Prabandham = %s AND PasuramNumber BETWEEN 1 AND 12
        """,
        (PRABANDHAM,),
    )
    cur.execute(
        f"""
        INSERT INTO {DD_TE} (SNo, PasuramNumber, DivyaDesam, SimilarNames)
        SELECT SNo, PasuramNumber, DivyaDesam, SimilarNames
        FROM {DD_SOURCE}
        WHERE PasuramNumber BETWEEN 1 AND 12
        """
    )


def fill_lipi_and_meaning(cur, meaning_map: dict[str, str]) -> tuple[int, int, int]:
    cur.execute(
        f"""
        SELECT Sno, Pasuram, Word, Meaning
        FROM {ARTHAM_TE}
        ORDER BY PasuramNumber, PattuNumber, PadhamNumber
        """
    )
    rows = cur.fetchall()
    lipi_fail = 0
    meaning_unsure = 0
    updates = []
    lipi_out = []
    meaning_out = []
    for sno, pasuram, word, meaning in rows:
        pasuram_te = tamil_to_telugu_lipi(pasuram)
        word_te = tamil_to_telugu_lipi(word)
        if not token_count_ok(pasuram, pasuram_te) or not token_count_ok(word, word_te):
            lipi_fail += 1
            pasuram_te = pasuram_te if token_count_ok(pasuram, pasuram_te) else None
            word_te = word_te if token_count_ok(word, word_te) else None
        meaning_key = meaning or ""
        meaning_te = meaning_map.get(meaning_key, "UNSURE") if meaning_key.strip() else "UNSURE"
        if meaning_te == "UNSURE":
            meaning_unsure += 1
        updates.append((pasuram_te, word_te, meaning_te, sno))
        lipi_out.append(
            {
                "Sno": sno,
                "Word": word,
                "Word_te": word_te or "",
                "Pasuram_te": (pasuram_te or "").replace("\r\n", " / "),
            }
        )
        meaning_out.append(
            {
                "Sno": sno,
                "Word": word,
                "Meaning": meaning,
                "Meaning_te": meaning_te,
                "review_flag": "UNSURE" if meaning_te == "UNSURE" else "OK",
            }
        )
    cur.executemany(
        f"UPDATE {ARTHAM_TE} SET Pasuram_te=%s, Word_te=%s, Meaning_te=%s WHERE Sno=%s",
        updates,
    )
    LIPI_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LIPI_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["Sno", "Word", "Word_te", "Pasuram_te"])
        writer.writeheader()
        writer.writerows(lipi_out)
    with MEANING_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["Sno", "Word", "Meaning", "Meaning_te", "review_flag"])
        writer.writeheader()
        writer.writerows(meaning_out)
    return len(rows), lipi_fail, meaning_unsure


def verify(cur, expected_rows: int) -> None:
    cur.execute(f"SELECT COUNT(DISTINCT PasuramNumber), COUNT(*) FROM {ARTHAM_TE}")
    n_pasurams, n_rows = cur.fetchone()
    if int(n_pasurams) != 12:
        raise SystemExit(f"FAIL: distinct pasurams={n_pasurams}, expected 12")
    if int(n_rows) != expected_rows:
        raise SystemExit(f"FAIL: padham rows={n_rows}, expected {expected_rows}")
    cur.execute(
        f"""
        SELECT COUNT(*) FROM {SOURCE_TABLE} s
        JOIN {ARTHAM_TE} t ON s.Sno = t.Sno
        WHERE s.Prabandham = %s AND s.PasuramNumber BETWEEN 1 AND 12
          AND (s.SimilarWords <=> t.SimilarWords) = 0
        """,
        (PRABANDHAM,),
    )
    drifted = cur.fetchone()[0]
    if drifted:
        raise SystemExit(f"FAIL: SimilarWords drifted on {drifted} rows")
    print(f"VERIFY ok: pasurams=12 rows={n_rows} similarwords_match=yes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("Choose one of --apply or --dry-run")
    if not args.apply and not args.dry_run:
        args.dry_run = True

    conn = connect(Path(args.config))
    cur = conn.cursor()
    n_pasurams, n_rows = source_counts(cur)
    print(f"source {SOURCE_TABLE}: pasurams={n_pasurams} padhams={n_rows}")
    if n_pasurams != 12:
        raise SystemExit("STOP: Thirupallandu distinct pasurams is not 12")

    cur.execute(
        f"""
        SELECT DISTINCT Meaning FROM {SOURCE_TABLE}
        WHERE Prabandham = %s AND PasuramNumber BETWEEN 1 AND 12
        """,
        (PRABANDHAM,),
    )
    meanings = [r[0] or "" for r in cur.fetchall()]

    if args.dry_run:
        print(f"dry-run: would clone {n_rows} rows, translate {len(meanings)} unique meanings")
        print(f"dry-run: would create {ARTHAM_TE} and {DD_TE}")
        conn.close()
        return

    cache = load_cache()
    cache = translate_meanings(meanings, cache)
    # Translation can outlive the MySQL wait_timeout; reconnect before DDL.
    conn.close()
    conn = connect(Path(args.config))
    cur = conn.cursor()
    create_tables(cur)
    copy_snapshot(cur)
    updated, lipi_fail, meaning_unsure = fill_lipi_and_meaning(cur, cache)
    conn.commit()
    verify(cur, n_rows)
    print(f"wrote {ARTHAM_TE} rows={updated} lipi_fail={lipi_fail} meaning_unsure={meaning_unsure}")
    print(f"review: {LIPI_CSV}")
    print(f"review: {MEANING_CSV}")
    conn.close()


if __name__ == "__main__":
    main()
