#!/usr/bin/env python3
"""Smoke-test a few padham / Āzhvār / Divyadesam search combos on prod (or --base).

Curated cases only — not a full Cartesian product. QA for the three search fields.
Does NOT affect Google indexing.

  poc/.venv/bin/python poc/scripts/smoke_search_combos.py
  poc/.venv/bin/python poc/scripts/smoke_search_combos.py --base https://nalayiram.in
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "poc" / "output" / "search_combos_smoke.csv"

RESULTS_RE = re.compile(
    r"Search Results for:\s*(.*?)\s*\((\d+)\s+results\)",
    re.IGNORECASE | re.DOTALL,
)
INPUT_VALUE_RE = re.compile(
    r'name=["\'](padhamPrefix|alwarPrefix|divyadesamPrefix)["\'][^>]*value=["\']([^"\']*)["\']',
    re.IGNORECASE,
)

# (label, query params, expect_results: True / False / None)
# None = only require HTTP 200
COMBOS: List[tuple[str, Dict[str, str], Optional[bool]]] = [
    # Single field
    ("padham_only_thiruppavai", {"padhamPrefix": "திருப்பாவை"}, True),
    ("alwar_only_andal", {"alwarPrefix": "ஆண்டாள்"}, True),
    # DivyaDesamTable stores bilingual names, e.g. "Thiruvarangam (Srirangam),ஸ்ரீரங்கம்"
    ("divyadesam_only_srirangam", {"divyadesamPrefix": "ஸ்ரீரங்கம்"}, True),
    # Two fields
    (
        "padham_alwar_pt",
        {"padhamPrefix": "பெரிய திருமொழி", "alwarPrefix": "திருமங்கையாழ்வார்"},
        True,
    ),
    (
        "padham_dd_nachiyar",
        {"padhamPrefix": "நாச்சியார் திருமொழி", "divyadesamPrefix": "ஸ்ரீரங்கம்"},
        True,
    ),
    (
        "alwar_dd_nammalwar",
        {"alwarPrefix": "நம்மாழ்வார்", "divyadesamPrefix": "திருகுருகூர்"},
        True,
    ),
    # Three fields (use DD substrings that exist for that prabandham)
    (
        "all_three_pt_naraiyur",
        {
            "padhamPrefix": "பெரிய திருமொழி",
            "alwarPrefix": "திருமங்கையாழ்வார்",
            "divyadesamPrefix": "நறையூர்",
        },
        True,
    ),
    (
        "all_three_thiruppavai",
        {
            "padhamPrefix": "திருப்பாவை",
            "alwarPrefix": "ஆண்டாள்",
            "divyadesamPrefix": "ஆய்ப்பாடி",
        },
        True,
    ),
    # Counts-page style prabandham filter
    (
        "prabandhamPrefix_periya",
        {"prabandhamPrefix": "பெரிய திருமொழி"},
        True,
    ),
    # English alias via padham (SEO maps to Tamil)
    ("english_thiruppavai", {"padhamPrefix": "Thiruppavai"}, True),
    # Expect no hits
    (
        "nonsense_empty",
        {
            "padhamPrefix": "zzz_no_such_padham_xyz",
            "alwarPrefix": "zzz_no_such_alwar_xyz",
            "divyadesamPrefix": "zzz_no_such_dd_xyz",
        },
        False,
    ),
]


@dataclass
class ComboResult:
    label: str
    url: str
    status: int
    ok: bool
    result_count: Optional[int]
    heading: str
    error: str


def build_url(base: str, params: Dict[str, str]) -> str:
    return f"{base.rstrip('/')}/index.php?{urlencode(params)}"


def check_combo(
    session: requests.Session,
    base: str,
    label: str,
    params: Dict[str, str],
    expect_results: Optional[bool],
    timeout: float,
) -> ComboResult:
    url = build_url(base, params)
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        status = response.status_code
        html = response.content.decode(
            response.apparent_encoding or "utf-8", errors="replace"
        )
        match = RESULTS_RE.search(html)
        result_count = int(match.group(2)) if match else None
        heading = re.sub(r"\s+", " ", match.group(0)).strip() if match else ""

        errors: List[str] = []
        if status != 200:
            errors.append(f"HTTP {status}")

        if expect_results is True:
            if not match:
                errors.append("missing Search Results heading")
            elif result_count is None or result_count < 1:
                errors.append(f"expected results>0, got {result_count}")
            # Form should echo at least one submitted term in the heading
            for key, value in params.items():
                if key == "prabandhamPrefix":
                    continue
                # English padham may be rewritten to Tamil in SEO layer before search
                if key == "padhamPrefix" and value.isascii() and value.lower() == "thiruppavai":
                    if "திருப்பாவை" not in heading and value not in heading:
                        errors.append("heading missing Thiruppavai/திருப்பாவை")
                elif value and value not in heading and key != "prabandhamPrefix":
                    # Alwar/DD/Tamil padham should appear in "Search Results for: …"
                    if key in ("padhamPrefix", "alwarPrefix", "divyadesamPrefix"):
                        if value not in heading:
                            errors.append(f"heading missing {key}={value}")

        elif expect_results is False:
            if match and result_count and result_count > 0:
                errors.append(f"expected empty, got {result_count} results")

        return ComboResult(
            label=label,
            url=url,
            status=status,
            ok=not errors,
            result_count=result_count,
            heading=heading[:200],
            error="; ".join(errors),
        )
    except Exception as exc:  # noqa: BLE001
        return ComboResult(
            label=label,
            url=url,
            status=0,
            ok=False,
            result_count=None,
            heading="",
            error=str(exc),
        )


def write_report(path: Path, rows: List[ComboResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["ok", "label", "status", "result_count", "heading", "url", "error"]
        )
        for row in rows:
            writer.writerow(
                [
                    "yes" if row.ok else "no",
                    row.label,
                    row.status,
                    row.result_count if row.result_count is not None else "",
                    row.heading,
                    row.url,
                    row.error,
                ]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="https://nalayiram.in")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--sleep", type=float, default=0.4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "NalayiramSearchComboSmoke/1.0 (+https://nalayiram.in; QA only)",
            "Accept": "text/html,application/xhtml+xml",
        }
    )

    results: List[ComboResult] = []
    print(f"Testing {len(COMBOS)} search combo(s) against {args.base}")
    for index, (label, params, expect) in enumerate(COMBOS, start=1):
        row = check_combo(session, args.base, label, params, expect, args.timeout)
        results.append(row)
        mark = "OK" if row.ok else "FAIL"
        count = row.result_count if row.result_count is not None else "-"
        print(f"[{index}/{len(COMBOS)}] {mark} {row.status} results={count} {label}")
        if not row.ok:
            print(f"         {row.error}")
            print(f"         {row.url}")
        if args.sleep > 0 and index < len(COMBOS):
            time.sleep(args.sleep)

    report = Path(args.report)
    write_report(report, results)
    failed = [r for r in results if not r.ok]
    print(f"\nWrote {report}")
    print(f"Passed {len(results) - len(failed)}/{len(results)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
