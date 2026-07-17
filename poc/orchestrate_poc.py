#!/usr/bin/env python3
"""Orchestrate the POC pipeline: scrape, transliterate, assemble, export, and optionally load."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from poc.config import load_config
from poc.generate_similar_words import finalize_records
from poc.json_exporter import export_to_json
from poc.scraper_adapter import scrape_range
from poc.transliterate_wrapper import TransliterationCache, Transliterator
from poc.transliterate_gpt_adapter import transliterate_with_public_html_script


def _is_comment_row(record: Dict) -> bool:
    padham = str(record.get("Padham", "")).strip().upper()
    if padham == "NOTE":
        return True

    word = str(record.get("Word", "")).strip()
    meaning = str(record.get("Meaning", "")).strip()
    return not padham and not word and bool(meaning)


def _normalize_comment_text(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized_lines: List[str] = []
    for line in lines:
        if line.startswith("(") and line.endswith(")"):
            normalized_lines.append(line)
            continue

        opens = line.count("(")
        closes = line.count(")")
        if opens < closes:
            line = "(" + line
        if closes < opens:
            line = line + ")"
        if not line.startswith("(") and not line.endswith(")"):
            line = f"({line})"
        normalized_lines.append(line)

    return " ".join(normalized_lines)


def _move_trailing_parenthetical_to_front(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""

    match = re.search(r'(\s*(?:\([^()]*\)\s*)+)$', text)
    if not match:
        return text

    trailing = match.group(1).strip()
    leading = text[: match.start(1)].strip()
    return f"{trailing} {leading}" if leading else trailing


def merge_comment_rows(records: List[Dict]) -> List[Dict]:
    """Merge NOTE / padham-less context rows into the first padham of each pasuram."""
    if not records:
        return []

    grouped: Dict[Any, List[Dict]] = {}
    order: List[Any] = []
    for record in records:
        pasuram_number = record.get("PasuramNumber")
        if pasuram_number not in grouped:
            order.append(pasuram_number)
            grouped[pasuram_number] = []
        grouped[pasuram_number].append(record)

    merged: List[Dict] = []
    for pasuram_number in order:
        merged.extend(_merge_comments_for_pasuram(grouped[pasuram_number]))
    return merged


def _append_comment_to_meaning(meaning: str, comment_text: str) -> str:
    meaning = _move_trailing_parenthetical_to_front(str(meaning or "").strip())
    comment_text = str(comment_text or "").strip()
    if not comment_text:
        return meaning
    if meaning:
        return f"{meaning} (- {comment_text})"
    return f"(- {comment_text})"


def _merge_comments_for_pasuram(rows: List[Dict]) -> List[Dict]:
    comments: List[str] = []
    padham_rows: List[Dict] = []

    for record in rows:
        if _is_comment_row(record):
            comment_text = _normalize_comment_text(record.get("Meaning") or record.get("Word") or "")
            if comment_text:
                comments.append(comment_text)
            continue

        padham_rows.append(dict(record))

    if not padham_rows:
        return []

    if comments:
        first = padham_rows[0]
        first["Meaning"] = _append_comment_to_meaning(
            str(first.get("Meaning", "")),
            " ".join(comments),
        )

    return padham_rows


def build_records(
    raw_records: List[Dict],
    transliterator: Transliterator,
    title: str,
    use_gpt_adapter: bool = False,
    gpt_script_path: Optional[Path] = None,
    gpt_dict_path: Optional[Path] = None,
    gpt_output_path: Optional[Path] = None,
) -> List[Dict]:
    padham_texts = [record["Padham"] for record in raw_records if record.get("Padham") and record.get("Padham") != "NOTE"]
    unique_padham = list(dict.fromkeys(padham_texts))

    if use_gpt_adapter:
        if not gpt_script_path or not gpt_dict_path or not gpt_output_path:
            raise ValueError("GPT adapter requires script_path, dict_path, and output_path")
        translations = transliterate_with_public_html_script(unique_padham, gpt_script_path, gpt_dict_path, gpt_output_path)
        mapping = {padham: translit for padham, translit in zip(unique_padham, translations)}
    else:
        mapping = transliterator.batch_translate(unique_padham)

    final: List[Dict] = []
    for record in raw_records:
        padham = record.get("Padham")
        if not padham or str(padham).strip().upper() == "NOTE":
            continue

        word = ""
        if padham != "NOTE":
            transliteration = mapping.get(padham, padham)
            word = f"{padham},{transliteration}"

        final.append(
            {
                **record,
                "Word": word,
                "Title": "",
                "PrabandhamTitle": title,
            }
        )

    final = finalize_records(final)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the POC automation pipeline")
    parser.add_argument("--config", default="poc/config.ini", help="Path to config file")
    parser.add_argument("--input-json", default=None, help="Use an existing JSON input file instead of scraping")
    parser.add_argument("--output", default="poc/output/pasurams_poc.json", help="Final JSON output")
    parser.add_argument("--load-db", action="store_true", help="Load the final JSON into MySQL")
    parser.add_argument("--use-gpt-adapter", action="store_true", help="Use the public_html transliterateGPT.py adapter")
    parser.add_argument("--dry-run-db", action="store_true", help="Validate DB load without inserting")
    args = parser.parse_args()

    config = load_config(args.config)
    cache = TransliterationCache(path=config.cache.path, ttl_seconds=config.cache.ttl_seconds)
    transliterator = Transliterator(cache=cache, transliteration_cmd=(config.transliteration.command.split() if config.transliteration.command else None), batch_size=config.transliteration.batch_size)

    output_path = Path(args.output)

    if args.input_json:
        input_path = Path(args.input_json)
        if not input_path.exists():
            raise FileNotFoundError(f"Input JSON not found: {input_path}")
        print(f"Loading existing JSON input: {input_path}")
        with open(input_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        raw_records = []
        if isinstance(data, dict):
            for values in data.values():
                if isinstance(values, list):
                    raw_records.extend(values)
        elif isinstance(data, list):
            raw_records = data
        else:
            raise ValueError("Unsupported JSON structure for input_json")

        raw_records = merge_comment_rows(raw_records)
        use_gpt_adapter = args.use_gpt_adapter or config.transliteration.use_gpt_adapter
        if use_gpt_adapter:
            gpt_script = Path(__file__).resolve().parent.parent / "public_html" / "transliterateGPT.py"
            gpt_dict = Path("poc/cache/transliterate_gpt_dict.json")
            gpt_output = Path("poc/output/transliterate_gpt_output.xlsx")
            final_records = build_records(
                raw_records,
                transliterator,
                title=config.scraper.title,
                use_gpt_adapter=True,
                gpt_script_path=gpt_script,
                gpt_dict_path=gpt_dict,
                gpt_output_path=gpt_output,
            )
        else:
            final_records = build_records(raw_records, transliterator, title=config.scraper.title)
    else:
        raw_records = scrape_range(
            base_url=config.scraper.base_url,
            start=config.scraper.start,
            end=config.scraper.end,
            prabandham=config.scraper.prabandham,
            title=config.scraper.title,
            alzwar=config.scraper.alzwar,
            pattu_number=config.scraper.pattu_number,
            pattu_number_start=config.scraper.pattu_number_start,
            output_path=Path("poc/output/scraped_pasurams.json"),
        )

        raw_records = merge_comment_rows(raw_records)

        use_gpt_adapter = args.use_gpt_adapter or config.transliteration.use_gpt_adapter
        if use_gpt_adapter:
            gpt_script = Path(__file__).resolve().parent.parent / "public_html" / "transliterateGPT.py"
            gpt_dict = Path("poc/cache/transliterate_gpt_dict.json")
            gpt_output = Path("poc/output/transliterate_gpt_output.xlsx")
            final_records = build_records(
                raw_records,
                transliterator,
                title=config.scraper.title,
                use_gpt_adapter=True,
                gpt_script_path=gpt_script,
                gpt_dict_path=gpt_dict,
                gpt_output_path=gpt_output,
            )
        else:
            final_records = build_records(raw_records, transliterator, title=config.scraper.title)

    export_to_json(final_records, output_path)

    if args.load_db:
        from poc.db_loader import load_json_to_db

        inserted = load_json_to_db(output_path, config.database, dry_run=args.dry_run_db)
        print(f"Inserted {inserted} records into {config.database.table}")


if __name__ == "__main__":
    main()
