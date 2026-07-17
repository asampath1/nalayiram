"""Shared tidley scraper helpers for பெரிய திருமொழி pathigams."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Sequence

from poc.scrapers.thiruvozhukootrirukkai_tidley import (
    PADHAVURAI_LABEL,
    PattuSection,
    _is_separator,
    _parse_table_rows,
    fetch_hentry_elements,
    format_pasuram_comma_lines,
    summarize_sections,
)

PRABANDHAM = "பெரிய திருமொழி"
ALZWAR = "திருமங்கையாழ்வார்"
VERSE_TAIL_RE = re.compile(r"[—–\-–\s]+\d+\s*[-—–]?\s*$")
PATHIGAM_SUFFIX_RE = re.compile(r"[—–\-–\s]*\d+-\d+-\d+\s*[-—–]?\s*$")
PATHIGAM_PARTIAL_SUFFIX_RE = re.compile(r"[—–\-–\s]*\d+-\d+\s*[-—–]?\s*$")
PATHIGAM_PATTU_IN_VERSE_RE = re.compile(r"(\d+)[-—–](\d+)[-—–](\d+)")
TitleMode = Literal["shared", "post_table_context"]


@dataclass(frozen=True)
class PathigamIngestConfig:
    tidley_url: str
    patham_number: int
    pathigam_number: int
    pasuram_number_base: int
    title_base: str
    title_mode: TitleMode = "shared"
    pathigam_name_tamil: str = ""
    pathigam_name_english: str = ""
    fixed_titles_by_pattu: Mapping[int, str] = field(default_factory=dict)


def pathigam_suffix(config: PathigamIngestConfig, pattu_number: int) -> str:
    return f"{config.patham_number}-{config.pathigam_number}-{pattu_number}"


def pattu_number_from_verse(text: str, config: PathigamIngestConfig) -> int:
    for match in PATHIGAM_PATTU_IN_VERSE_RE.finditer(text):
        patham, pathigam, pattu = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if patham == config.patham_number and pathigam == config.pathigam_number:
            return pattu
    raise RuntimeError(f"Could not parse pathigam suffix from verse: {text[:100]!r}")


def _verse_text_has_pathigam_suffix(text: str, config: PathigamIngestConfig) -> bool:
    try:
        pattu_number_from_verse(text, config)
    except RuntimeError:
        return False
    return True


def pathigam_search_aliases(config: PathigamIngestConfig, pattu_number: int) -> List[str]:
    a, b, c = config.patham_number, config.pathigam_number, pattu_number
    return [f"{a}.{b}.{c}", f"{a}-{b}-{c}", f"{a} {b} {c}"]


def pathigam_name_aliases(config: PathigamIngestConfig) -> List[str]:
    aliases: List[str] = []
    if config.pathigam_name_tamil.strip():
        aliases.append(config.pathigam_name_tamil.strip())
    if config.pathigam_name_english.strip():
        aliases.append(config.pathigam_name_english.strip())
    return aliases


def all_pathigam_aliases(config: PathigamIngestConfig, pattu_number: int) -> List[str]:
    return pathigam_search_aliases(config, pattu_number) + pathigam_name_aliases(config)


def pasuram_start(config: PathigamIngestConfig) -> int:
    return config.pasuram_number_base + 1


def pasuram_end(config: PathigamIngestConfig, pattu_count: int) -> int:
    return config.pasuram_number_base + pattu_count


def _clean_verse_text(text: str, config: PathigamIngestConfig, pattu_number: int) -> str:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        return ""

    cleaned: List[str] = []
    suffix = pathigam_suffix(config, pattu_number)
    for index, line in enumerate(raw_lines):
        if index < len(raw_lines) - 1:
            line = VERSE_TAIL_RE.sub("", line).strip()
        else:
            line = PATHIGAM_SUFFIX_RE.sub("", line)
            line = PATHIGAM_PARTIAL_SUFFIX_RE.sub("", line)
            line = VERSE_TAIL_RE.sub("", line).strip()
            line = f"{line} –{suffix}"
        if line:
            cleaned.append(line)
    return format_pasuram_comma_lines("\n".join(cleaned))


def _verse_before_padhavurai(
    elements: Sequence[Any],
    padhavurai_index: int,
    config: PathigamIngestConfig,
    pattu_number: int,
) -> str:
    raw = _raw_verse_before_padhavurai(elements, padhavurai_index, config)
    return _clean_verse_text(raw, config, pattu_number)


def _raw_verse_before_padhavurai(
    elements: Sequence[Any],
    padhavurai_index: int,
    config: PathigamIngestConfig | None = None,
) -> str:
    index = padhavurai_index - 1
    fallback = ""
    while index >= 0:
        element = elements[index]
        if element.name == "p":
            text = element.get_text("\n", strip=True)
            if text and text != PADHAVURAI_LABEL:
                if config and _verse_text_has_pathigam_suffix(text, config):
                    return text
                if not fallback:
                    fallback = text
        index -= 1
    return fallback


def _wrap_context_paragraph(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text.startswith("(") and text.endswith(")"):
        return text
    if text.startswith("(") or text.startswith("["):
        return text
    return f"({text})"


def _first_paragraph_after_table(elements: Sequence[Any], table_index: int) -> str:
    for index in range(table_index + 1, len(elements)):
        element = elements[index]
        if element.name == "table":
            break
        if element.name != "p":
            continue
        text = element.get_text(strip=True)
        if not text or text == PADHAVURAI_LABEL or _is_separator(text):
            continue
        return text
    return ""


def _build_title(
    config: PathigamIngestConfig,
    *,
    pattu_number: int = 0,
    context_paragraph: str = "",
) -> str:
    fixed = config.fixed_titles_by_pattu.get(pattu_number)
    if fixed:
        return fixed.strip()
    base = config.title_base.strip()
    if config.title_mode == "shared":
        return base
    context = _wrap_context_paragraph(context_paragraph)
    if context:
        return f"{base}\n{context}"
    return base


def parse_pattu_sections(
    config: PathigamIngestConfig,
    elements: Sequence[Any] | None = None,
) -> List[PattuSection]:
    if elements is None:
        elements = fetch_hentry_elements(config.tidley_url)

    padhavurai_indices = [
        index
        for index, element in enumerate(elements)
        if element.name == "p" and element.get_text(strip=True) == PADHAVURAI_LABEL
    ]
    if not padhavurai_indices:
        raise RuntimeError(f"No {PADHAVURAI_LABEL} sections found on page")

    sections: List[PattuSection] = []
    for padhavurai_index in padhavurai_indices:
        raw_pasuram = _raw_verse_before_padhavurai(elements, padhavurai_index, config)
        if not raw_pasuram:
            raise RuntimeError(f"Could not find pasuram verse before {PADHAVURAI_LABEL}")

        pattu_number = pattu_number_from_verse(raw_pasuram, config)
        table_index = padhavurai_index + 1
        if table_index >= len(elements) or elements[table_index].name != "table":
            raise RuntimeError(
                f"Pattu {pattu_number}: expected table immediately after {PADHAVURAI_LABEL}"
            )

        pasuram = _clean_verse_text(raw_pasuram, config, pattu_number)
        if not pasuram:
            raise RuntimeError(f"Pattu {pattu_number}: could not find pasuram verse")

        padham_rows = _parse_table_rows(elements[table_index])
        if not padham_rows:
            raise RuntimeError(f"Pattu {pattu_number}: table has no padham rows")

        context_paragraph = ""
        if config.title_mode == "post_table_context":
            context_paragraph = _first_paragraph_after_table(elements, table_index)

        sections.append(
            PattuSection(
                pattu_number=pattu_number,
                pasuram=pasuram,
                title=_build_title(
                    config,
                    pattu_number=pattu_number,
                    context_paragraph=context_paragraph,
                ),
                padham_rows=padham_rows,
            )
        )

    sections.sort(key=lambda section: section.pattu_number)
    return sections


def sections_to_records(
    sections: Sequence[PattuSection],
    config: PathigamIngestConfig,
    *,
    prabandham: str = PRABANDHAM,
    alzwar: str = ALZWAR,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for section in sections:
        pasuram_number = config.pasuram_number_base + section.pattu_number
        aliases = ",".join(all_pathigam_aliases(config, section.pattu_number))
        for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
            records.append(
                {
                    "Prabandham": prabandham,
                    "PasuramNumber": pasuram_number,
                    "Pasuram": section.pasuram,
                    "PattuNumber": section.pattu_number,
                    "Padham": padham,
                    "Meaning": meaning,
                    "Alzwar": alzwar,
                    "PadhamNumber": padham_number,
                    "Title": section.title,
                    "Word": "",
                    "SimilarWords": "",
                    "NithyaanusandhamIndex": None,
                    "PrabandhamTitle": prabandham,
                    "PathigamAliases": aliases,
                }
            )
    return records


def apply_pathigam_aliases(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    for record in records:
        row = dict(record)
        aliases = row.pop("PathigamAliases", "")
        similar = str(row.get("SimilarWords", "") or "").strip()
        if aliases:
            similar = f"{similar},{aliases}" if similar else aliases
        row["SimilarWords"] = similar
        updated.append(row)
    return updated


def write_review_csv(
    sections: Sequence[PattuSection],
    config: PathigamIngestConfig,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "PattuNumber",
                "PasuramNumber",
                "PadhamNumber",
                "Padham",
                "Meaning",
                "Pasuram",
                "Title",
                "padham_count",
            ]
        )
        for section in sections:
            pasuram_number = config.pasuram_number_base + section.pattu_number
            for padham_number, (padham, meaning) in enumerate(section.padham_rows, start=1):
                writer.writerow(
                    [
                        section.pattu_number,
                        pasuram_number,
                        padham_number,
                        padham,
                        meaning,
                        section.pasuram.replace("\n", " / "),
                        section.title.replace("\n", " / "),
                        len(section.padham_rows),
                    ]
                )


__all__ = [
    "ALZWAR",
    "PRABANDHAM",
    "PathigamIngestConfig",
    "apply_pathigam_aliases",
    "parse_pattu_sections",
    "pasuram_end",
    "pasuram_start",
    "pattu_number_from_verse",
    "all_pathigam_aliases",
    "pathigam_suffix",
    "sections_to_records",
    "summarize_sections",
    "write_review_csv",
]
