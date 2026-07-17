"""Manual Title overrides for tidley scrapes (vetting corrections)."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Dict, List

from poc.title_scrapers.base import PasuramTitleRecord, join_title_blocks

ROOT = Path(__file__).resolve().parent.parent


def load_title_overrides(path: Path) -> Dict[int, str]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    overrides: Dict[int, str] = {}
    for pasuram_number, title in raw.items():
        normalized = join_title_blocks([str(title)])
        overrides[int(pasuram_number)] = normalized
    return overrides


def apply_title_overrides(
    records: List[PasuramTitleRecord],
    overrides: Dict[int, str],
) -> List[PasuramTitleRecord]:
    if not overrides:
        return records

    return [
        replace(record, title=overrides[record.pasuram_number])
        if record.pasuram_number in overrides
        else record
        for record in records
    ]


def apply_overrides_from_file(
    records: List[PasuramTitleRecord],
    override_path: Path,
) -> List[PasuramTitleRecord]:
    return apply_title_overrides(records, load_title_overrides(override_path))


def apply_title_prefix(
    records: List[PasuramTitleRecord],
    prefix: str,
    *,
    from_pasuram_number: int,
) -> List[PasuramTitleRecord]:
    """Prepend a shared prefix to titles from the given pasuram number onward."""
    normalized_prefix = join_title_blocks([prefix]).strip()
    updated: List[PasuramTitleRecord] = []

    for record in records:
        if record.pasuram_number < from_pasuram_number:
            updated.append(record)
            continue

        title = record.title.strip()
        if title.startswith(normalized_prefix):
            updated.append(record)
            continue

        updated.append(
            replace(record, title=f"{normalized_prefix} {title}".strip())
        )

    return updated
