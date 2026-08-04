#!/usr/bin/env python3
"""Apply Titles for பெரிய திருமொழி நான்காம் பத்து (1248-1347) from poc/pasuram.txt → POC.

Title format:
  (4-1–போதலர்ந்த) (திருத்தேவனார் தொகை) - (ஸ்ரீ பெரியவாச்சான் பிள்ளை)
  (commentary)

4-8-1 .. 4-8-6 share one title block; 4-8-7 .. 4-8-10 use per-verse commentary from pasuram.txt.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config
from poc.transliterate_gpt_adapter import transliterate_with_public_html_script

PASURAM_TXT = ROOT / "poc" / "pasuram.txt"
POC_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu4_poc.json"
TITLES_JSON = ROOT / "poc" / "output" / "periya_thirumozhi_patthu4_titles.json"
AUTHOR = "ஸ்ரீ பெரியவாச்சான் பிள்ளை"
PASURAM_START = 1248
PASURAM_END = 1347

PATHIGAM_META: Dict[str, Dict[str, str]] = {
    "4-1": {"start": "1248", "end": "1257", "short_name": "போதலர்ந்த", "divyadesam": "திருத்தேவனார் தொகை"},
    "4-2": {"start": "1258", "end": "1267", "short_name": "கம்பாமா", "divyadesam": "திருவண் புருடோத்தம்"},
    "4-3": {"start": "1268", "end": "1277", "short_name": "பேரணிந்து", "divyadesam": "திருநாங்கூர்ச் செம்பொன் செய்கோயில்"},
    "4-4": {"start": "1278", "end": "1287", "short_name": "மாற்றரசர்", "divyadesam": "திருநாங்கூர்த் திருத்தெற்றியம்பலம்"},
    "4-5": {"start": "1288", "end": "1297", "short_name": "தூம்புடைப", "divyadesam": "திருநாங்கூர்த் திருமணிக்கூடம்"},
    "4-6": {"start": "1298", "end": "1307", "short_name": "தாவளந்து", "divyadesam": "திருநாங்கூர்க் காவளம்பாடி"},
    "4-7": {"start": "1308", "end": "1317", "short_name": "கண்ணார் கடல்", "divyadesam": "திருநாங்கூர்த் திருவெள்ளக்குளம்"},
    "4-8": {"start": "1318", "end": "1327", "short_name": "கவளயானை", "divyadesam": "திருநாங்கூர்ப் பார்த்தன்பள்ளி"},
    "4-9": {"start": "1328", "end": "1337", "short_name": "நும்மைத் தொழுதோம்", "divyadesam": "திருவிந்தளூர்"},
    "4-10": {"start": "1338", "end": "1347", "short_name": "ஆய்ச்சியர்", "divyadesam": "திருவெள்ளியங்குடி"},
}

SHARED_4_8_COMMENTARY = (
    "திருமாலிடத்து ஈடுபட்ட தலைமகளது செயல்கண்டு நற்றாய் இரங்கிக் கூறுதல்\n"
    "திருவடிகளிலே விழுந்து சரணம் புக்கு-அடியேன் இடரைக் களையாய் -என்று\n"
    "தேவரோட்டை அனுபவத்துக்கு விரோதியைப் போக்கித் தர வேணும் என்று அபேஷித்தார்\n"
    "அவனும் அப்படியே செய்வானாக ஒருப்பட-அது பற்றாமல்-ப்ராப்தியால் உண்டான த்வரையாலே\n"
    "தாமான தன்மை போய்-பிரிந்து-பிரிவாற்றாமையாலே நோவு பட்டு"
)

SUFFIX_FIND_RE = re.compile(
    r"(?<![0-9])(4-(?:10|[1-9])-(?:10|[1-9]))\s*-?",
    re.UNICODE,
)
SEP_LINE_RE = re.compile(r"^[—–\-−_]{4,}\s*$", re.MULTILINE)


def normalize_ws(text: str) -> str:
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return " ".join(line for line in lines if line).strip(" –-\t")


def code_for_pasuram(pasuram_number: int) -> str:
    return f"4-{(pasuram_number - PASURAM_START) // 10 + 1}"


def pasuram_for_suffix(suffix: str) -> int:
    _, pathigam_s, pattu_s = suffix.split("-")
    return PASURAM_START + (int(pathigam_s) - 1) * 10 + (int(pattu_s) - 1)


def extract_blocks(raw: str) -> List[Tuple[str, str]]:
    first = None
    for match in SUFFIX_FIND_RE.finditer(raw):
        if match.group(1) != "4-1-1":
            continue
        probe = raw[max(0, match.start() - 8) : match.start()]
        if any("\u0b80" <= ch <= "\u0bff" for ch in probe):
            first = match
            break
    if first is None:
        raise RuntimeError("Could not find verse marker 4-1-1")

    ordered: List[re.Match[str]] = []
    seen: set[str] = set()
    for match in SUFFIX_FIND_RE.finditer(raw):
        if match.start() < first.start():
            continue
        suffix = match.group(1)
        if suffix in seen:
            continue
        _, a, b = suffix.split("-")
        if not (1 <= int(a) <= 10 and 1 <= int(b) <= 10):
            continue
        seen.add(suffix)
        ordered.append(match)

    blocks: List[Tuple[str, str]] = []
    for index, match in enumerate(ordered):
        content_start = match.end()
        content_end = ordered[index + 1].start() if index + 1 < len(ordered) else len(raw)
        chunk = raw[content_start:content_end]
        sep = SEP_LINE_RE.search(chunk)
        if sep:
            chunk = chunk[: sep.start()]
        commentary = normalize_ws(chunk)
        blocks.append((match.group(1), commentary))
    return blocks


def build_title_for(code: str, short_name: str, divyadesam: str, commentary: str) -> str:
    header = f"({code}–{short_name}) ({divyadesam}) - ({AUTHOR})"
    body = commentary.strip()
    if body and not (body.startswith("(") and body.endswith(")")):
        body = f"({body})"
    elif not body:
        body = "()"
    return f"{header}\n{body}"


def parse_titles(path: Path) -> Dict[int, Dict[str, str]]:
    raw = path.read_text(encoding="utf-8")
    blocks = {suffix: commentary for suffix, commentary in extract_blocks(raw)}
    titles: Dict[int, Dict[str, str]] = {}

    for code, info in PATHIGAM_META.items():
        start_n = int(info["start"])
        end_n = int(info["end"])
        for pasuram_number in range(start_n, end_n + 1):
            pathigam_idx = (pasuram_number - PASURAM_START) // 10 + 1
            pattu_idx = (pasuram_number - PASURAM_START) % 10 + 1
            suffix = f"4-{pathigam_idx}-{pattu_idx}"

            if code == "4-8" and pattu_idx <= 6:
                commentary = SHARED_4_8_COMMENTARY
            else:
                commentary = blocks.get(suffix, "")

            titles[pasuram_number] = {
                "pathigam_code": code,
                "short_name": info["short_name"],
                "divyadesam": info["divyadesam"],
                "commentary": commentary,
                "title": build_title_for(
                    code, info["short_name"], info["divyadesam"], commentary
                ),
                "suffix": suffix,
            }

    missing = [n for n in range(PASURAM_START, PASURAM_END + 1) if n not in titles]
    empty: List[int] = []
    for n, info in titles.items():
        pattu_idx = (n - PASURAM_START) % 10 + 1
        if code_for_pasuram(n) == "4-8" and pattu_idx <= 6:
            continue
        if not info["commentary"].strip("()"):
            empty.append(n)
    if missing:
        print(f"WARNING: missing title blocks for: {missing}")
    if empty:
        print(f"WARNING: empty commentary for: {sorted(empty)}")
    if len(titles) != 100:
        raise RuntimeError(f"Expected 100 titles, got {len(titles)}; missing={missing}")
    return titles


def build_heading_aliases(titles: Dict[int, Dict[str, str]]) -> Dict[int, List[str]]:
    pathigams: Dict[str, Dict[str, Any]] = {}
    for pasuram_number, info in titles.items():
        code = info["pathigam_code"]
        bucket = pathigams.setdefault(code, {"short_name": info["short_name"], "numbers": []})
        bucket["numbers"].append(pasuram_number)
    short_names = [meta["short_name"] for meta in pathigams.values()]
    translations = transliterate_with_public_html_script(
        short_names,
        ROOT / "public_html" / "transliterateGPT.py",
        Path("poc/cache/transliterate_gpt_dict.json"),
        Path("poc/output/transliterate_pathigam_headings_patthu4.xlsx"),
    )
    name_to_eng = dict(zip(short_names, translations))
    aliases_by_pasuram: Dict[int, List[str]] = {}
    for code, meta in pathigams.items():
        tamil = meta["short_name"]
        eng = name_to_eng[tamil]
        eng_compact = re.sub(r"\s+", "", eng)
        if eng_compact and eng_compact[0].islower():
            eng_compact = eng_compact[0].upper() + eng_compact[1:]
        aliases = [
            f"{code} {tamil}",
            f"{code}–{tamil}",
            f"{code}-{eng_compact}",
            tamil,
            eng,
        ]
        print(f"{code}: {aliases[0]} | {aliases[1]}")
        for n in meta["numbers"]:
            aliases_by_pasuram[n] = aliases
    return aliases_by_pasuram


def apply_to_json(titles: Dict[int, Dict[str, str]], json_path: Path) -> int:
    if not json_path.exists():
        print(f"JSON not found yet: {json_path}")
        return 0
    records = json.loads(json_path.read_text(encoding="utf-8"))
    aliases = build_heading_aliases(titles)
    updated = 0
    for row in records:
        n = int(row["PasuramNumber"])
        info = titles.get(n)
        if not info:
            continue
        row["Title"] = info["title"]
        similar = str(row.get("SimilarWords") or "")
        for alias in aliases.get(n, []):
            if alias and alias not in similar:
                similar = f"{similar},{alias}" if similar else alias
        row["SimilarWords"] = similar
        updated += 1
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated


def apply_to_db(titles: Dict[int, Dict[str, str]], config_path: Path) -> int:
    config = load_config(str(config_path))
    db = config.database
    aliases = build_heading_aliases(titles)
    conn = mysql.connector.connect(
        host=db.host, port=db.port, user=db.user, password=db.password, database=db.database
    )
    cur = conn.cursor()
    updated = 0
    try:
        for n, info in sorted(titles.items()):
            cur.execute(
                f"SELECT SimilarWords FROM {db.table} "
                f"WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி' LIMIT 1",
                (n,),
            )
            row = cur.fetchone()
            similar = (row[0] if row else "") or ""
            for alias in aliases.get(n, []):
                if alias and alias not in similar:
                    similar = f"{similar},{alias}" if similar else alias
            cur.execute(
                f"""
                UPDATE {db.table}
                SET Title=%s, SimilarWords=%s
                WHERE PasuramNumber=%s AND Prabandham='பெரிய திருமொழி'
                """,
                (info["title"], similar, n),
            )
            updated += cur.rowcount
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument("--pasuram-txt", default=str(PASURAM_TXT))
    parser.add_argument("--poc-json", default=str(POC_JSON))
    parser.add_argument("--titles-json", default=str(TITLES_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    titles = parse_titles(Path(args.pasuram_txt))
    Path(args.titles_json).write_text(
        json.dumps({str(k): v for k, v in titles.items()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Parsed {len(titles)} titles → {args.titles_json}")
    for n in (1248, 1257, 1318, 1324, 1347):
        print(n, titles[n]["title"][:160].replace("\n", " | "))
    if args.dry_run and not args.apply:
        print("Dry run only.")
        return
    if not args.apply:
        print("Use --apply to update POC JSON + DB.")
        return
    print(f"JSON rows updated: {apply_to_json(titles, Path(args.poc_json))}")
    print(f"DB rows updated: {apply_to_db(titles, Path(args.config))}")


if __name__ == "__main__":
    main()
