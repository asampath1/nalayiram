"""Build pathigam search aliases from release-note link source."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from poc.scripts.build_newreleasenote_poc import (
    LINK_RE,
    RANGE_RE,
    LinkEntry,
    classify_entries,
    parse_links,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HTML = ROOT / "poc" / "data" / "release_notes_link_source.html"

GROUP_PRABANDHAM = {
    "periyazhwar": "பெரியாழ்வார் திருமொழி",
    "nachiyar": "நாச்சியார் திருமொழி",
    "perumal_thirumozhi": "பெருமாள் திருமொழி",
    "periya_thirumozhi": "பெரிய திருமொழி",
    "thiruvaimozhi": "திருவாய்மொழி",
}

PATHIGAM_GROUPS = tuple(GROUP_PRABANDHAM.keys())

# (start, end) -> (code, short_name) — user-validated overrides
RANGE_OVERRIDES: Dict[Tuple[int, int], Tuple[str, str]] = {
    (108, 117): ("1-9", "வட்டு நடுவே"),
    (152, 161): ("2-4", "நீராட்டம்"),
    (182, 191): ("2-7", "பூச்சூடல்"),
    (192, 201): ("2-8", "காப்பிடல்"),
    (948, 957): ("1-1", "வாடினேன் வாடி"),
    (968, 977): ("1-3", "முற்ற மூத்து"),
}

# Extra aliases to merge (same pasuram range as RANGE_OVERRIDES key)
EXTRA_ALIASES: Dict[Tuple[int, int], List[str]] = {
    (108, 117): ["1-9 வட்டநடுவே"],
}


@dataclass(frozen=True)
class PathigamSpec:
    group: str
    prabandham: str
    code: str
    short_name: str
    start: int
    end: int

    @property
    def alias(self) -> str:
        if re.fullmatch(r"\d+-\d+", self.code):
            return f"{self.code} {self.short_name}"
        return f"{self.code}-{self.short_name}"

    @property
    def padham_prefix(self) -> str:
        return self.alias.replace(" ", "+")

    @property
    def range_key(self) -> Tuple[int, int]:
        return (self.start, self.end)

    def all_aliases(self) -> List[str]:
        aliases = [self.alias]
        aliases.extend(EXTRA_ALIASES.get(self.range_key, []))
        return aliases


def _parse_label(title: str) -> Tuple[str, str] | None:
    title = RANGE_RE.sub("", title).strip()
    if title.startswith("பெரிய திருமொழி "):
        return None
    match = re.match(r"^(\d+-\d+)\s+(.+)$", title)
    if match:
        return match.group(1), match.group(2).strip()
    match = re.match(r"^(\d+)-(.+)$", title)
    if match:
        return match.group(1), match.group(2).strip()
    return None


def _spec_from_parts(
    group: str,
    code: str,
    short_name: str,
    start: int,
    end: int,
) -> PathigamSpec:
    return PathigamSpec(
        group=group,
        prabandham=GROUP_PRABANDHAM[group],
        code=code,
        short_name=short_name,
        start=start,
        end=end,
    )


def build_pathigam_catalog(
    source_html: str | None = None,
) -> Dict[Tuple[int, int], PathigamSpec]:
    raw = source_html if source_html is not None else SOURCE_HTML.read_text(encoding="utf-8")
    entries = parse_links(raw)
    groups = classify_entries(entries)
    catalog: Dict[Tuple[int, int], PathigamSpec] = {}

    for group in PATHIGAM_GROUPS:
        for entry in groups.get(group, []):
            if entry.start is None or entry.end is None:
                continue
            key = (entry.start, entry.end)
            if key in RANGE_OVERRIDES:
                code, short_name = RANGE_OVERRIDES[key]
                catalog[key] = _spec_from_parts(group, code, short_name, entry.start, entry.end)
                continue
            if key in catalog:
                continue
            title = RANGE_RE.sub("", entry.label).strip()
            parsed = _parse_label(title)
            if parsed:
                code, short_name = parsed
                catalog[key] = _spec_from_parts(
                    group, code, short_name, entry.start, entry.end
                )

    for key, (code, short_name) in RANGE_OVERRIDES.items():
        if key in catalog:
            continue
        start, end = key
        group = _group_for_range(start, end, groups)
        if group:
            catalog[key] = _spec_from_parts(group, code, short_name, start, end)

    return dict(sorted(catalog.items(), key=lambda item: item[0][0]))


def _group_for_range(
    start: int,
    end: int,
    groups: Dict[str, List[LinkEntry]],
) -> str | None:
    for group in PATHIGAM_GROUPS:
        for entry in groups.get(group, []):
            if entry.start == start and entry.end == end:
                return group
    if 13 <= start <= 473:
        return "periyazhwar"
    if 504 <= start <= 646:
        return "nachiyar"
    if 647 <= start <= 751:
        return "perumal_thirumozhi"
    if 948 <= start <= 1447:
        return "periya_thirumozhi"
    if 2675 <= start <= 3776:
        return "thiruvaimozhi"
    return None


def aliases_by_pasuram(catalog: Iterable[PathigamSpec]) -> Dict[Tuple[str, int], List[str]]:
    by_key: Dict[Tuple[str, int], List[str]] = {}
    for spec in catalog:
        for pasuram_number in range(spec.start, spec.end + 1):
            key = (spec.prabandham, pasuram_number)
            bucket = by_key.setdefault(key, [])
            for alias in spec.all_aliases():
                if alias not in bucket:
                    bucket.append(alias)
    return by_key


def merge_aliases(similar: str, aliases: List[str]) -> str:
    for alias in aliases:
        if alias and alias not in similar:
            similar = f"{similar},{alias}" if similar else alias
    return similar


def rewrite_link_source(html_text: str, catalog: Dict[Tuple[int, int], PathigamSpec]) -> str:
    def replace_link(match: re.Match[str]) -> str:
        href, raw_label = match.group(1), match.group(2)
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw_label))).strip()
        range_match = RANGE_RE.search(label)
        if not range_match:
            return match.group(0)
        start = int(range_match.group(1))
        end = int(range_match.group(2) or start)
        spec = catalog.get((start, end))
        if spec is None:
            return match.group(0)
        new_href = re.sub(
            r"padhamPrefix=[^&\"]+",
            f"padhamPrefix={spec.padham_prefix}",
            href,
        )
        range_label = f"({start}-{end})" if start != end else f"({start})"
        new_label = f"{spec.alias} {range_label}"
        return f'<a href="{new_href}">{html.escape(new_label)}</a>'

    return LINK_RE.sub(replace_link, html_text)
