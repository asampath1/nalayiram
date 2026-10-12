#!/usr/bin/env python3
"""Smoke-test prod SEO URLs (sitemap hubs + prabandham landings).

Checks HTTP status, <title>, canonical, and meta description.
Does NOT submit to Google or affect indexing — QA only.

  poc/.venv/bin/python poc/scripts/smoke_seo_prabandham_urls.py
  poc/.venv/bin/python poc/scripts/smoke_seo_prabandham_urls.py --base https://nalayiram.in
  poc/.venv/bin/python poc/scripts/smoke_seo_prabandham_urls.py --english-aliases --limit 5
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urlparse, parse_qs

import requests

ROOT = Path(__file__).resolve().parents[2]
SITEMAP = ROOT / "public_html" / "sitemap.xml"
SEO_PHP = ROOT / "public_html" / "seo_prabandhams.php"
DEFAULT_REPORT = ROOT / "poc" / "output" / "seo_prabandham_smoke.csv"

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
CANON_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
# href before rel also allowed
CANON_RE_ALT = re.compile(
    r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
    re.IGNORECASE,
)
DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
DESC_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',
    re.IGNORECASE,
)
TA_ROW_RE = re.compile(
    r"\['ta'\s*=>\s*'((?:\\'|[^'])*)'\s*,\s*'en'\s*=>\s*\[([^\]]*)\]",
    re.UNICODE,
)
EN_STR_RE = re.compile(r"'((?:\\'|[^'])*)'")


@dataclass
class CheckResult:
    url: str
    kind: str
    expected_ta: str
    status: int
    ok: bool
    title: str
    canonical: str
    description: str
    error: str


def parse_sitemap_locs(path: Path) -> List[str]:
    root = ET.parse(path).getroot()
    # handle default xmlns
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [el.text.strip() for el in root.findall("sm:url/sm:loc", ns) if el.text]
    if not locs:
        locs = [el.text.strip() for el in root.findall("url/loc") if el.text]
    return locs


def load_catalog_from_php(path: Path) -> List[Tuple[str, List[str]]]:
    text = path.read_text(encoding="utf-8")
    rows: List[Tuple[str, List[str]]] = []
    for match in TA_ROW_RE.finditer(text):
        ta = match.group(1).replace("\\'", "'")
        en = [m.group(1).replace("\\'", "'") for m in EN_STR_RE.finditer(match.group(2))]
        rows.append((ta, en))
    if not rows:
        raise RuntimeError(f"Could not parse prabandham catalog from {path}")
    return rows


def extract_meta(html: str) -> Tuple[str, str, str]:
    title_m = TITLE_RE.search(html)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    canon_m = CANON_RE.search(html) or CANON_RE_ALT.search(html)
    canonical = canon_m.group(1).strip() if canon_m else ""
    desc_m = DESC_RE.search(html) or DESC_RE_ALT.search(html)
    description = desc_m.group(1).strip() if desc_m else ""
    return title, canonical, description


def padham_from_url(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    raw = (qs.get("padhamPrefix") or qs.get("prabandhamPrefix") or [""])[0]
    return unquote(raw).replace("+", " ").strip()


def classify_url(url: str) -> str:
    path = urlparse(url).path
    if path.rstrip("/").endswith("sitemap.xml") or url.rstrip("/").endswith("nalayiram.in"):
        return "hub"
    if "newreleasenotes" in path:
        return "hub"
    if "divyaprabandham_counts" in path or "divyadesam_alwar_matrix" in path:
        return "hub"
    if "padhamPrefix=" in url or "prabandhamPrefix=" in url:
        return "prabandham"
    return "other"


def check_url(
    session: requests.Session,
    url: str,
    kind: str,
    expected_ta: str,
    timeout: float,
) -> CheckResult:
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        status = response.status_code
        html = response.text if response.encoding or True else ""
        # force utf-8 decode when possible
        if response.content:
            html = response.content.decode(response.apparent_encoding or "utf-8", errors="replace")
        title, canonical, description = extract_meta(html)
        errors: List[str] = []
        if status != 200:
            errors.append(f"HTTP {status}")
        if kind == "prabandham":
            if not expected_ta:
                expected_ta = padham_from_url(url)
            if expected_ta and expected_ta not in title:
                errors.append("title missing Tamil prabandham")
            if "Padhavurai Search" not in title and "Nalayiram" not in title:
                errors.append("title missing SEO suffix")
            if not canonical:
                errors.append("missing canonical")
            elif expected_ta and quote(expected_ta, safe="") not in canonical and expected_ta not in unquote(canonical):
                errors.append("canonical not prabandham URL")
            if not description:
                errors.append("missing description")
            elif expected_ta and expected_ta not in description:
                errors.append("description missing Tamil prabandham")
        else:
            if not title:
                errors.append("missing title")
        return CheckResult(
            url=url,
            kind=kind,
            expected_ta=expected_ta,
            status=status,
            ok=not errors,
            title=title[:180],
            canonical=canonical,
            description=description[:180],
            error="; ".join(errors),
        )
    except Exception as exc:  # noqa: BLE001 — report all fetch failures
        return CheckResult(
            url=url,
            kind=kind,
            expected_ta=expected_ta,
            status=0,
            ok=False,
            title="",
            canonical="",
            description="",
            error=str(exc),
        )


def build_targets(
    base: str,
    include_sitemap: bool,
    include_english: bool,
    limit: Optional[int],
) -> List[Tuple[str, str, str]]:
    """Return list of (url, kind, expected_ta)."""
    targets: List[Tuple[str, str, str]] = []
    catalog = load_catalog_from_php(SEO_PHP)
    ta_set = {ta for ta, _ in catalog}

    if include_sitemap:
        for loc in parse_sitemap_locs(SITEMAP):
            # allow overriding host for local/staging smoke
            if base.rstrip("/") != "https://nalayiram.in":
                parsed = urlparse(loc)
                loc = base.rstrip("/") + parsed.path + (("?" + parsed.query) if parsed.query else "")
            kind = classify_url(loc)
            expected = padham_from_url(loc) if kind == "prabandham" else ""
            if kind == "prabandham" and expected and expected not in ta_set:
                # still check, but mark expected from URL
                pass
            targets.append((loc, kind, expected))

    if include_english:
        for ta, en_list in catalog:
            if not en_list:
                continue
            en = en_list[0]
            url = f"{base.rstrip('/')}/index.php?padhamPrefix={quote(en)}"
            targets.append((url, "prabandham", ta))

    # de-dupe preserving order
    seen = set()
    unique: List[Tuple[str, str, str]] = []
    for item in targets:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    if limit is not None:
        unique = unique[:limit]
    return unique


def write_report(path: Path, rows: Iterable[CheckResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["ok", "kind", "status", "expected_ta", "url", "title", "canonical", "description", "error"]
        )
        for row in rows:
            writer.writerow(
                [
                    "yes" if row.ok else "no",
                    row.kind,
                    row.status,
                    row.expected_ta,
                    row.url,
                    row.title,
                    row.canonical,
                    row.description,
                    row.error,
                ]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="https://nalayiram.in", help="Site origin to test")
    parser.add_argument("--sitemap", default=str(SITEMAP))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--sleep", type=float, default=0.4, help="Delay between requests (seconds)")
    parser.add_argument("--limit", type=int, default=None, help="Only first N URLs")
    parser.add_argument(
        "--english-aliases",
        action="store_true",
        help="Also hit primary English alias URLs (mapped to Tamil SEO)",
    )
    parser.add_argument(
        "--no-sitemap",
        action="store_true",
        help="Skip sitemap URLs (use with --english-aliases)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global SITEMAP
    SITEMAP = Path(args.sitemap)

    targets = build_targets(
        base=args.base,
        include_sitemap=not args.no_sitemap,
        include_english=args.english_aliases,
        limit=args.limit,
    )
    if not targets:
        print("No URLs to test.")
        sys.exit(1)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "NalayiramSeoSmoke/1.0 (+https://nalayiram.in; QA only)",
            "Accept": "text/html,application/xhtml+xml",
        }
    )

    results: List[CheckResult] = []
    print(f"Testing {len(targets)} URL(s) against {args.base}")
    for index, (url, kind, expected_ta) in enumerate(targets, start=1):
        result = check_url(session, url, kind, expected_ta, timeout=args.timeout)
        results.append(result)
        mark = "OK" if result.ok else "FAIL"
        print(f"[{index}/{len(targets)}] {mark} {result.status} {kind}: {url}")
        if not result.ok:
            print(f"         {result.error}")
            if result.title:
                print(f"         title={result.title}")
        if args.sleep > 0 and index < len(targets):
            time.sleep(args.sleep)

    report_path = Path(args.report)
    write_report(report_path, results)
    failed = [r for r in results if not r.ok]
    print(f"\nWrote {report_path}")
    print(f"Passed {len(results) - len(failed)}/{len(results)}")
    if failed:
        print("Failures:")
        for row in failed:
            print(f"  - {row.url}: {row.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
