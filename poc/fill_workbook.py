#!/usr/bin/env python3
"""Fill Excel workbook rows: Word, Title, SimilarWords (incl. pasuram-wide MB tagging). POC only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from poc.config import load_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.transliterate_gpt_adapter import transliterate_with_public_html_script
from poc.transliterate_wrapper import TransliterationCache, Transliterator

TITLE_BY_PRABANDHAM = {
    "ஸ்ரீ திருச்சந்த விருத்தம்": "ஸ்ரீ திருச்சந்த விருத்தம், Sri Thiruchanda Viruttam",
    "பெருமாள் திருமொழி": "பெருமாள் திருமொழி, Perumal ThiruMozhi",
    "முதல் திருவந்தாதி": "முதல் திருவந்தாதி, Mudhal Thiruvandhathi",
    "இரண்டாம் திருவந்தாதி": "இரண்டாம் திருவந்தாதி, Irandam Thiruvandhathi",
    "மூன்றாம் திருவந்தாதி": "மூன்றாம் திருவந்தாதி, Moonraam Thiruvandhathi",
    "நான்முகன் திருவந்தாதி": "நான்முகன் திருவந்தாதி, Nanmugan Thiruvandhathi",
}

# PasuramNumber at PattuNumber 1 for each Thiruvandhathi prabandham (Pattu = PasuramNumber - base).
PATTU_BASE_BY_PRABANDHAM = {
    "முதல் திருவந்தாதி": 2081,
    "இரண்டாம் திருவந்தாதி": 2181,
    "மூன்றாம் திருவந்தாதி": 2281,
    "நான்முகன் திருவந்தாதி": 2381,
}


def pattu_number_for(prabandham: str, pasuram_number: Optional[int], excel_pattu: Optional[int]) -> Optional[int]:
    """PattuNumber within prabandham: 2182→1 … 2281→100; 2282→1 … 2381→100."""
    base = PATTU_BASE_BY_PRABANDHAM.get(prabandham)
    if base is not None and pasuram_number is not None:
        return pasuram_number - base
    return excel_pattu

COLUMNS = [
    "Sno",
    "Prabandham",
    "PasuramNumber",
    "Pasuram",
    "PattuNumber",
    "Word",
    "SimilarWords",
    "Padham",
    "Meaning",
    "Alzwar",
    "PadhamNumber",
    "Title",
]


def _safe_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize(text: Any) -> str:
    if text is None:
        return ""
    if isinstance(text, float) and pd.isna(text):
        return ""
    value = str(text).strip()
    if value.lower() == "nan":
        return ""
    return value


def excel_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    padham_seq_by_pasuram: Dict[Any, int] = {}
    for _, row in df.iterrows():
        padham = _normalize(row.get("Padham"))
        if not padham or padham.upper() == "NOTE":
            continue

        prabandham = _normalize(row.get("Prabandham"))
        pasuram_number = _safe_int(row.get("PasuramNumber"))
        # Title column = per-pasuram commentary (green in UI), not prabandham name.
        title_commentary = _normalize(row.get("Title"))
        prabandham_title = TITLE_BY_PRABANDHAM.get(prabandham, prabandham)

        padham_number = _safe_int(row.get("PadhamNumber"))
        if padham_number is None and pasuram_number is not None:
            padham_seq_by_pasuram[pasuram_number] = padham_seq_by_pasuram.get(pasuram_number, 0) + 1
            padham_number = padham_seq_by_pasuram[pasuram_number]

        pattu_number = pattu_number_for(
            prabandham,
            pasuram_number,
            _safe_int(row.get("PattuNumber")),
        )

        records.append(
            {
                "Prabandham": prabandham,
                "PasuramNumber": pasuram_number,
                "Pasuram": _normalize(row.get("Pasuram")),
                "PattuNumber": pattu_number,
                "Padham": padham,
                "Meaning": _normalize(row.get("Meaning")),
                "Alzwar": _normalize(row.get("Alzwar")),
                "PadhamNumber": padham_number,
                "Title": title_commentary,
                "PrabandhamTitle": prabandham_title,
                "Word": "",
                "SimilarWords": "",
                "NithyaanusandhamIndex": None,
            }
        )
    return records


def build_transliterator(config_path: Path) -> Transliterator:
    config = load_config(str(config_path))
    cache = TransliterationCache(path=config.cache.path, ttl_seconds=config.cache.ttl_seconds)
    cmd = None
    if config.transliteration.command:
        cmd = config.transliteration.command.split()
    return Transliterator(cache=cache, transliteration_cmd=cmd, batch_size=config.transliteration.batch_size)


def transliterate_records(records: List[Dict[str, Any]], transliterator: Transliterator) -> List[Dict[str, Any]]:
    padhams = list(dict.fromkeys(r["Padham"] for r in records if r.get("Padham")))
    mapping = transliterator.batch_translate(padhams)
    updated: List[Dict[str, Any]] = []
    for record in records:
        padham = record["Padham"]
        translit = mapping.get(padham, padham)
        updated.append({**record, "Word": f"{padham}, {translit}"})
    return updated


def transliterate_records_from_config(
    records: List[Dict[str, Any]],
    config_path: Path,
    *,
    gpt_script_path: Optional[Path] = None,
    gpt_dict_path: Optional[Path] = None,
    gpt_output_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Transliterate padhams using cache/command or GPT adapter per config.ini."""
    config = load_config(str(config_path))
    padhams = list(dict.fromkeys(r["Padham"] for r in records if r.get("Padham")))
    if not padhams:
        return records

    if config.transliteration.use_gpt_adapter:
        script = gpt_script_path or (ROOT / "public_html" / "transliterateGPT.py")
        dict_path = gpt_dict_path or Path("poc/cache/transliterate_gpt_dict.json")
        output_path = gpt_output_path or Path("poc/output/transliterate_gpt_output.xlsx")
        translations = transliterate_with_public_html_script(
            padhams, script, dict_path, output_path
        )
        mapping = {padham: translit for padham, translit in zip(padhams, translations)}
    else:
        transliterator = build_transliterator(config_path)
        mapping = transliterator.batch_translate(padhams)

    updated: List[Dict[str, Any]] = []
    for record in records:
        padham = record["Padham"]
        translit = mapping.get(padham, padham)
        updated.append({**record, "Word": f"{padham}, {translit}"})
    return updated


def records_to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        rows.append({col: record.get(col) for col in COLUMNS})
    return pd.DataFrame(rows, columns=COLUMNS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill workbook with Word, Title, SimilarWords")
    parser.add_argument("--input", default="Thiruvandhathi2and3.xlsx")
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--config", default="poc/config.ini")
    parser.add_argument(
        "--output-xlsx",
        default="Thiruvandhathi2and3_filled.xlsx",
    )
    parser.add_argument(
        "--output-json",
        default="poc/output/thiruvandhathi_filled.json",
    )
    parser.add_argument(
        "--detectors-dir",
        default="lookupsimilarwords/detectors",
    )
    parser.add_argument(
        "--themes",
        default="all",
        help="Theme ids (comma-separated) or 'all'",
    )
    parser.add_argument(
        "--no-themes",
        action="store_true",
        help="Skip pasuram-wide theme SimilarWords tagging",
    )
    parser.add_argument(
        "--no-mb",
        action="store_true",
        help="Alias for --no-themes",
    )
    parser.add_argument(
        "--detector",
        default="lookupsimilarwords/detectors/mahabharatham_detector.json",
        help="Legacy single-detector path (used only if detectors dir is empty)",
    )
    parser.add_argument(
        "--approved-mb-pasurams",
        default=None,
        help="JSON file with mb_pasuram_numbers list to force MB tag (overrides auto-detect)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    df = pd.read_excel(input_path, sheet_name=args.sheet or 0)
    records = excel_to_records(df)
    print(f"Loaded {len(records)} padham rows from {input_path}")

    transliterator = build_transliterator(Path(args.config))
    records = transliterate_records(records, transliterator)

    from lookupsimilarwords.theme_registry import resolve_theme_ids

    skip_themes = args.no_themes or args.no_mb
    theme_ids = None if args.themes == "all" else resolve_theme_ids(args.themes)
    detectors_dir = Path(args.detectors_dir)
    detector_path = Path(args.detector) if not skip_themes else None
    records = finalize_records(
        records,
        apply_themes=not skip_themes,
        themes=theme_ids,
        detectors_dir=detectors_dir,
        detector_path=detector_path,
    )

    if args.approved_mb_pasurams:
        with open(args.approved_mb_pasurams, encoding="utf-8") as fh:
            approved = json.load(fh)
        approved_nums = set(approved.get("mb_pasuram_numbers", []))
        from lookupsimilarwords.pasuram_themes import append_theme_aliases, load_theme_detector

        mb_path = detectors_dir / "mahabharatham_detector.json"
        if not mb_path.exists():
            mb_path = Path(args.detector)
        detector = load_theme_detector(mb_path)
        aliases = detector.get("aliases", ["மகாபாரதம்", "mahabharatham"])
        for record in records:
            if record.get("PasuramNumber") in approved_nums:
                record["SimilarWords"] = append_theme_aliases(record.get("SimilarWords", ""), aliases)

    themed_rows = sum(
        1
        for r in records
        if any(
            tag in str(r.get("SimilarWords", ""))
            for tag in ("மகாபாரதம்", "Ramayanam", "சிவன்", "Gajendran", "sangu", "chakaram", "வாமனன்")
        )
    )
    print(f"Rows with theme tags in SimilarWords: {themed_rows}")

    out_df = records_to_dataframe(records)
    out_xlsx = Path(args.output_xlsx)
    out_df.to_excel(out_xlsx, index=False, sheet_name="Thiruvandhathi-filled")
    print(f"Wrote {out_xlsx}")

    export_to_json(records, Path(args.output_json))


if __name__ == "__main__":
    main()
