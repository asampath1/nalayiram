#!/usr/bin/env python3
"""Build POC padham-usage reports from PasuramsArthamTablePOC (read-only).

Never INSERT/UPDATE/DELETE pasuram tables. Writes a display JSON for
public_html/padham_reports.php.

  poc/.venv/bin/python poc/scripts/build_padham_reports.py --dry-run
  poc/.venv/bin/python poc/scripts/build_padham_reports.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import mysql.connector

from poc.config import load_config

CLUSTERS_JSON = ROOT / "poc" / "data" / "padham_clusters.json"
NOTES_JSON = ROOT / "poc" / "data" / "padham_report_notes.json"
SEED_JSON = ROOT / "public_html" / "divyaprabandham_counts_seed.json"
THEME_REGISTRY = ROOT / "lookupsimilarwords" / "theme_registry.json"
OUT_JSON = ROOT / "public_html" / "data" / "padham_reports_poc.json"

TOP_CORPUS_EXACT = 50
TOP_PRABANDHAM_EXACT = 10
TOP_PRABANDHAM_CLUSTERS = 5
TOP_ALWAR_EXACT = 10
TOP_ALWAR_CLUSTERS = 5
TOP_THEME_PADHAMS = 10
TOP_CROSS = 50
MIN_CROSS_OCC = 5
TOP_CLUSTER_PAIRS = 15
BATCH_SIZE = 1000

# Canonical 12 Āzhvārs (includes Āṇḍāḷ and Madhurakavi). Order matches counts seed.
CANONICAL_ALWARS: List[str] = [
    "பொய்கையாழ்வார்",
    "பூதத்தாழ்வார்",
    "பேயாழ்வார்",
    "திருமழிசை ஆழ்வார்",
    "நம்மாழ்வார்",
    "மதுரகவியாழ்வார்",
    "குலசேகர ஆழ்வார்",
    "பெரியாழ்வார்",
    "ஆண்டாள்",
    "தொண்டரடிப்பொடிஆழ்வார்",
    "திருப்பாண் ஆழ்வார்",
    "திருமங்கையாழ்வார்",
]

# Āchārya works left out of padham research (Āzhvār pasurams only).
EXCLUDED_PRABANDHAMS = frozenset(
    {
        "இராமாநுச நூற்றந்தாதி",
        "உபதேச ரத்னமாலை",
        "திருவாய்மொழி நூற்றந்தாதி",
    }
)

# Padham-cluster id → SimilarWords theme id (தீம் column on corpus cluster table).
CLUSTER_THEME_MAP: Dict[str, str] = {
    "vamana": "vamanan",
    "narasimha": "narasimha",
    "rama": "ramayana",
    "garuda": "garudan",
    "sangu": "sangu",
    "chakkaram": "chakkaram",
    "aazhi": "chakkaram",
}

# Matrix uses theme-tagged pasuram counts for these clusters (ஆழி stays padham lines;
# its தீம் column still shows the shared சக்கரம் total).
MATRIX_THEME_CLUSTERS = frozenset(
    {"vamana", "narasimha", "rama", "garuda", "sangu", "chakkaram"}
)

ALWAR_ALIASES: Dict[str, str] = {
    "திருமழிசையாழ்வார்": "திருமழிசை ஆழ்வார்",
    "திருமழிசை ஆழ்வார்": "திருமழிசை ஆழ்வார்",
}


def nfc(text: Any) -> str:
    return unicodedata.normalize("NFC", str(text or "")).strip()


def is_tamil_padham(padham: str) -> bool:
    """True if the token contains at least one Tamil letter (skip Latin padham rows)."""
    return any("\u0b80" <= ch <= "\u0bff" for ch in padham)


def canonical_alwar(raw: Any) -> str:
    name = nfc(raw).replace("\r", "").replace("\n", " ")
    name = " ".join(name.split())
    return ALWAR_ALIASES.get(name, name)


def is_eligible_padham(padham: str) -> bool:
    if not padham:
        return False
    return padham.upper() != "NOTE"


def pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * part / whole, 2)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_clusters(
    path: Path,
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]], Dict[str, List[str]]]:
    data = load_json(path)
    clusters = data["clusters"]
    stems: List[Tuple[str, str]] = []
    blocked: Dict[str, List[str]] = {}
    for cluster in clusters:
        cid = cluster["id"]
        blocked[cid] = [nfc(b) for b in cluster.get("blocked_substrings") or [] if nfc(b)]
        for stem in cluster.get("stems") or []:
            stem_n = nfc(stem)
            if stem_n:
                stems.append((stem_n, cid))
    stems.sort(key=lambda item: (-len(item[0]), item[0], item[1]))
    return clusters, stems, blocked


def match_cluster(
    padham: str,
    stems: Sequence[Tuple[str, str]],
    blocked: Dict[str, List[str]],
) -> Optional[str]:
    for stem, cid in stems:
        if stem not in padham:
            continue
        if any(b in padham for b in blocked.get(cid) or []):
            continue
        return cid
    return None


def load_theme_aliases(path: Path) -> List[Dict[str, Any]]:
    registry = load_json(path)
    themes = []
    for theme_id, cfg in registry.get("themes", {}).items():
        aliases = [nfc(a) for a in cfg.get("aliases") or [] if nfc(a)]
        if not aliases:
            continue
        padham_seeds = [nfc(s) for s in cfg.get("padham_substring_seeds") or [] if nfc(s)]
        themes.append(
            {
                "theme_id": theme_id,
                "concept": nfc(cfg.get("concept") or theme_id),
                "aliases": aliases,
                "aliases_lower": [a.lower() for a in aliases],
                "padham_seeds": padham_seeds or aliases,
                "search_alias": aliases[0],
            }
        )
    themes.sort(key=lambda t: t["theme_id"])
    return themes


def prabandham_order(seed: List[dict]) -> List[Tuple[str, str]]:
    """Return (prabandham, alwar) in seed sort_order, carrying Alwar down groups."""
    out: List[Tuple[str, str]] = []
    current_alwar = ""
    for row in sorted(seed, key=lambda r: int(r["sort_order"])):
        alwar = nfc(row.get("alwar") or "") or current_alwar
        if nfc(row.get("alwar") or ""):
            current_alwar = alwar
        prabandham = nfc(row["prabandham"])
        out.append((prabandham, alwar))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build POC padham analytics JSON (read-only)")
    parser.add_argument("--config", default="poc/config.ini", help="DB config (POC only)")
    parser.add_argument("--apply", action="store_true", help="Write public_html/data/padham_reports_poc.json")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only; do not write")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    return parser.parse_args()


class Counter:
    __slots__ = ("occ", "pasurams")

    def __init__(self) -> None:
        self.occ = 0
        self.pasurams: Set[int] = set()

    def add(self, pn: int) -> None:
        self.occ += 1
        self.pasurams.add(pn)


def rank_counters(
    counters: Dict[str, Counter],
    total_rows: int,
    total_pasurams: int,
    limit: int,
    notes: Dict[str, str],
) -> List[Dict[str, Any]]:
    items = sorted(counters.items(), key=lambda kv: (-kv[1].occ, kv[0]))[:limit]
    rows = []
    for key, c in items:
        row = {
            "token": key,
            "occ": c.occ,
            "occ_pct": pct(c.occ, total_rows),
            "pasurams": len(c.pasurams),
            "pasuram_pct": pct(len(c.pasurams), total_pasurams),
        }
        note = notes.get(key) or ""
        if note:
            row["note"] = note
        rows.append(row)
    return rows


def cluster_rank(
    counters: Dict[str, Counter],
    clusters_by_id: Dict[str, Dict[str, Any]],
    total_rows: int,
    total_pasurams: int,
    limit: int,
    notes: Dict[str, str],
) -> List[Dict[str, Any]]:
    items = sorted(counters.items(), key=lambda kv: (-kv[1].occ, kv[0]))[:limit]
    rows = []
    for cid, c in items:
        meta = clusters_by_id.get(cid) or {}
        row = {
            "id": cid,
            "label_ta": meta.get("label_ta") or cid,
            "label_en": meta.get("label_en") or cid,
            "search": meta.get("label_ta") or cid,
            "stems": list(meta.get("stems") or []),
            "blocked_substrings": list(meta.get("blocked_substrings") or []),
            "occ": c.occ,
            "occ_pct": pct(c.occ, total_rows),
            "pasurams": len(c.pasurams),
            "pasuram_pct": pct(len(c.pasurams), total_pasurams),
        }
        note = notes.get(cid) or ""
        if note:
            row["note"] = note
        rows.append(row)
    return rows


def fetch_rows(cursor, table: str, batch_size: int) -> Iterable[dict]:
    cursor.execute(
        f"SELECT PasuramNumber, Alzwar, Prabandham, Padham, SimilarWords FROM `{table}`"
    )
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            yield row


def build_report(
    rows: Iterable[dict],
    clusters: List[Dict[str, Any]],
    stems: Sequence[Tuple[str, str]],
    blocked: Dict[str, List[str]],
    notes: Dict[str, Any],
    themes: List[Dict[str, Any]],
    prabandham_rows: List[Tuple[str, str]],
) -> Dict[str, Any]:
    clusters_by_id = {c["id"]: c for c in clusters}
    exact_notes = notes.get("exact") or {}
    cluster_notes = notes.get("clusters") or {}
    prabandham_notes = notes.get("prabandhams") or {}
    alwar_notes = notes.get("alwars") or {}
    theme_notes = notes.get("themes") or {}

    corpus_exact: Dict[str, Counter] = defaultdict(Counter)
    corpus_clusters: Dict[str, Counter] = defaultdict(Counter)
    by_prabandham_exact: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_prabandham_cluster: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_alwar_exact: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_alwar_cluster: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    prabandham_rows_n: Dict[str, int] = defaultdict(int)
    prabandham_pasurams: Dict[str, Set[int]] = defaultdict(set)
    alwar_rows_n: Dict[str, int] = defaultdict(int)
    alwar_pasurams: Dict[str, Set[int]] = defaultdict(set)

    padham_alwars: Dict[str, Set[str]] = defaultdict(set)
    padham_prabandhams: Dict[str, Set[str]] = defaultdict(set)

    cluster_alwar_occ: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    theme_alwar_pasurams: Dict[str, Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))

    pasuram_clusters: Dict[int, Set[str]] = defaultdict(set)
    pasuram_themes: Dict[int, Set[str]] = defaultdict(set)
    pasuram_padhams: Dict[int, List[str]] = defaultdict(list)

    eligible_rows = 0
    eligible_pasurams: Set[int] = set()
    skipped_thaniyan = 0
    skipped_empty = 0
    skipped_excluded = 0
    unique_padhams: Set[str] = set()

    for row in rows:
        try:
            pn = int(row["PasuramNumber"])
        except (TypeError, ValueError):
            continue
        prabandham = nfc(row.get("Prabandham"))
        if prabandham in EXCLUDED_PRABANDHAMS:
            skipped_excluded += 1
            continue
        padham = nfc(row.get("Padham"))
        if pn == 0:
            skipped_thaniyan += 1
            continue
        if not is_eligible_padham(padham):
            skipped_empty += 1
            # Verse exists but this row has no padham text.
            eligible_pasurams.add(pn)
            prabandham_pasurams[prabandham].add(pn)
            alwar = canonical_alwar(row.get("Alzwar"))
            if alwar in CANONICAL_ALWARS:
                alwar_pasurams[alwar].add(pn)
            continue

        alwar = canonical_alwar(row.get("Alzwar"))
        similar = nfc(row.get("SimilarWords"))

        eligible_rows += 1
        eligible_pasurams.add(pn)
        unique_padhams.add(padham)

        if is_tamil_padham(padham):
            corpus_exact[padham].add(pn)
            by_prabandham_exact[prabandham][padham].add(pn)
            padham_prabandhams[padham].add(prabandham)
            if alwar in CANONICAL_ALWARS:
                by_alwar_exact[alwar][padham].add(pn)
                padham_alwars[padham].add(alwar)

        prabandham_rows_n[prabandham] += 1
        prabandham_pasurams[prabandham].add(pn)
        pasuram_padhams[pn].append(padham)

        if alwar in CANONICAL_ALWARS:
            alwar_rows_n[alwar] += 1
            alwar_pasurams[alwar].add(pn)

        cid = match_cluster(padham, stems, blocked)
        if cid:
            corpus_clusters[cid].add(pn)
            by_prabandham_cluster[prabandham][cid].add(pn)
            pasuram_clusters[pn].add(cid)
            if alwar in CANONICAL_ALWARS:
                by_alwar_cluster[alwar][cid].add(pn)
                cluster_alwar_occ[cid][alwar].add(pn)

        if similar:
            similar_l = similar.lower()
            for theme in themes:
                if any(alias in similar_l for alias in theme["aliases_lower"]):
                    pasuram_themes[pn].add(theme["theme_id"])
                    if alwar in CANONICAL_ALWARS:
                        theme_alwar_pasurams[theme["theme_id"]][alwar].add(pn)

    total_pasurams = len(eligible_pasurams)

    corpus_exact_ranked = rank_counters(
        corpus_exact, eligible_rows, total_pasurams, TOP_CORPUS_EXACT, exact_notes
    )
    corpus_cluster_ranked = cluster_rank(
        corpus_clusters,
        clusters_by_id,
        eligible_rows,
        total_pasurams,
        len(clusters_by_id),
        cluster_notes,
    )

    prabandham_out = []
    for prabandham, seed_alwar in prabandham_rows:
        n_rows = prabandham_rows_n.get(prabandham, 0)
        if n_rows <= 0:
            continue
        n_pas = len(prabandham_pasurams[prabandham])
        block = {
            "prabandham": prabandham,
            "alwar": seed_alwar,
            "eligible_rows": n_rows,
            "eligible_pasurams": n_pas,
            "top_exact": rank_counters(
                by_prabandham_exact[prabandham],
                n_rows,
                n_pas,
                TOP_PRABANDHAM_EXACT,
                exact_notes,
            ),
            "top_clusters": cluster_rank(
                by_prabandham_cluster[prabandham],
                clusters_by_id,
                n_rows,
                n_pas,
                TOP_PRABANDHAM_CLUSTERS,
                cluster_notes,
            ),
        }
        note = prabandham_notes.get(prabandham) or ""
        if note:
            block["note"] = note
        prabandham_out.append(block)

    alwar_out = []
    for alwar in CANONICAL_ALWARS:
        n_rows = alwar_rows_n.get(alwar, 0)
        if n_rows <= 0:
            continue
        n_pas = len(alwar_pasurams[alwar])
        block = {
            "alwar": alwar,
            "eligible_rows": n_rows,
            "eligible_pasurams": n_pas,
            "top_exact": rank_counters(
                by_alwar_exact[alwar], n_rows, n_pas, TOP_ALWAR_EXACT, exact_notes
            ),
            "top_clusters": cluster_rank(
                by_alwar_cluster[alwar],
                clusters_by_id,
                n_rows,
                n_pas,
                TOP_ALWAR_CLUSTERS,
                cluster_notes,
            ),
        }
        note = alwar_notes.get(alwar) or ""
        if note:
            block["note"] = note
        alwar_out.append(block)

    common: List[Dict[str, Any]] = []
    unique_alwar: List[Dict[str, Any]] = []
    unique_prabandham: List[Dict[str, Any]] = []
    canonical_set = set(CANONICAL_ALWARS)
    for padham, c in corpus_exact.items():
        if c.occ < MIN_CROSS_OCC:
            continue
        alwars = padham_alwars.get(padham) or set()
        prs = padham_prabandhams.get(padham) or set()
        item = {
            "token": padham,
            "occ": c.occ,
            "occ_pct": pct(c.occ, eligible_rows),
            "pasurams": len(c.pasurams),
            "pasuram_pct": pct(len(c.pasurams), total_pasurams),
            "alwars": sorted(alwars),
            "prabandhams": sorted(prs),
        }
        note = exact_notes.get(padham) or ""
        if note:
            item["note"] = note
        if alwars >= canonical_set:
            common.append(item)
        if len(alwars) == 1:
            item = dict(item)
            item["alwar"] = next(iter(alwars))
            unique_alwar.append(item)
        if len(prs) == 1:
            item_p = {
                "token": padham,
                "occ": c.occ,
                "occ_pct": pct(c.occ, eligible_rows),
                "pasurams": len(c.pasurams),
                "pasuram_pct": pct(len(c.pasurams), total_pasurams),
                "prabandham": next(iter(prs)),
            }
            if note:
                item_p["note"] = note
            unique_prabandham.append(item_p)

    common.sort(key=lambda r: (-r["occ"], r["token"]))
    unique_alwar.sort(key=lambda r: (-r["occ"], r["token"]))
    unique_prabandham.sort(key=lambda r: (-r["occ"], r["token"]))

    theme_alias_by_id = {th["theme_id"]: th.get("search_alias") or th["concept"] for th in themes}

    theme_pasuram_n: Dict[str, int] = defaultdict(int)
    for ids in pasuram_themes.values():
        for tid in ids:
            theme_pasuram_n[tid] += 1
    for row in corpus_cluster_ranked:
        tid = CLUSTER_THEME_MAP.get(row["id"])
        if not tid:
            continue
        row["theme_id"] = tid
        row["theme_alias"] = theme_alias_by_id.get(tid, "")
        row["theme_pasurams"] = int(theme_pasuram_n.get(tid, 0))

    cluster_by_alwar = []
    for cluster in clusters:
        cid = cluster["id"]
        theme_id = CLUSTER_THEME_MAP.get(cid)
        use_theme = cid in MATRIX_THEME_CLUSTERS and bool(theme_id)
        per = []
        for alwar in CANONICAL_ALWARS:
            if use_theme:
                n = len(theme_alwar_pasurams[theme_id].get(alwar) or set())
                per.append({"alwar": alwar, "occ": n, "pasurams": n})
            else:
                c = cluster_alwar_occ[cid].get(alwar)
                per.append(
                    {
                        "alwar": alwar,
                        "occ": c.occ if c else 0,
                        "pasurams": len(c.pasurams) if c else 0,
                    }
                )
        cluster_by_alwar.append(
            {
                "id": cid,
                "label_ta": cluster["label_ta"],
                "label_en": cluster["label_en"],
                "search": cluster["label_ta"],
                "stems": list(cluster.get("stems") or []),
                "blocked_substrings": list(cluster.get("blocked_substrings") or []),
                "theme_id": theme_id if use_theme else None,
                "theme_alias": theme_alias_by_id.get(theme_id or "", "") if use_theme else "",
                "metric": "theme_pasurams" if use_theme else "padham_occ",
                "total": sum(p["occ"] for p in per),
                "by_alwar": per,
            }
        )

    theme_out = []
    for theme in themes:
        tagged = sorted(pn for pn, ids in pasuram_themes.items() if theme["theme_id"] in ids)
        seeds = [s for s in (theme.get("padham_seeds") or []) if len(s) >= 3]
        block = {
            "theme_id": theme["theme_id"],
            "concept": theme["concept"],
            "search_alias": theme.get("search_alias") or theme["concept"],
            "aliases": theme.get("aliases") or [],
            "tagged_pasurams": len(tagged),
            "top_padhams": [],
        }
        note = theme_notes.get(theme["theme_id"]) or ""
        if note:
            block["note"] = note
        if not tagged:
            theme_out.append(block)
            continue
        tagged_set = set(tagged)
        counters: Dict[str, Counter] = defaultdict(Counter)
        for pn in tagged_set:
            for padham in pasuram_padhams.get(pn, []):
                if seeds and not any(seed in padham for seed in seeds):
                    continue
                counters[padham].add(pn)
        if not counters:
            for pn in tagged_set:
                for padham in pasuram_padhams.get(pn, []):
                    counters[padham].add(pn)
        seed_rows = sum(c.occ for c in counters.values())
        block["top_padhams"] = rank_counters(
            counters, seed_rows, len(tagged_set), TOP_THEME_PADHAMS, exact_notes
        )
        theme_out.append(block)

    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    top_cluster_ids = [r["id"] for r in corpus_cluster_ranked[:TOP_CLUSTER_PAIRS]]
    top_set = set(top_cluster_ids)
    for pn, cids in pasuram_clusters.items():
        present = sorted(cids & top_set)
        for i, a in enumerate(present):
            for b in present[i + 1 :]:
                pair_counts[(a, b)] += 1
    cluster_pairs = []
    for (a, b), n in sorted(pair_counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))[:40]:
        cluster_pairs.append(
            {
                "a": a,
                "a_label": clusters_by_id[a]["label_ta"],
                "a_stems": list(clusters_by_id[a].get("stems") or []),
                "a_blocked": list(clusters_by_id[a].get("blocked_substrings") or []),
                "b": b,
                "b_label": clusters_by_id[b]["label_ta"],
                "b_stems": list(clusters_by_id[b].get("stems") or []),
                "b_blocked": list(clusters_by_id[b].get("blocked_substrings") or []),
                "pasurams": n,
            }
        )

    payload = {
        "meta": {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_table": "PasuramsArthamTablePOC",
            "eligible_rows": eligible_rows,
            "eligible_pasurams": total_pasurams,
            "unique_padhams": len(unique_padhams),
            "skipped_thaniyan_rows": skipped_thaniyan,
            "skipped_empty_or_note": skipped_empty,
            "skipped_excluded_rows": skipped_excluded,
            "excluded_prabandhams": sorted(EXCLUDED_PRABANDHAMS),
            "min_cross_occ": MIN_CROSS_OCC,
        },
        "corpus_exact": corpus_exact_ranked,
        "corpus_clusters": corpus_cluster_ranked,
        "prabandhams": prabandham_out,
        "alwars": alwar_out,
        "cross_alwar": {
            "min_occ": MIN_CROSS_OCC,
            "common_to_all_alwars": common,
            "unique_to_one_alwar": unique_alwar[:TOP_CROSS],
            "unique_to_one_prabandham": unique_prabandham[:TOP_CROSS],
            "cluster_by_alwar": cluster_by_alwar,
        },
        "themes": theme_out,
        "cluster_pairs": cluster_pairs,
    }
    return payload


def print_summary(payload: Dict[str, Any]) -> None:
    meta = payload["meta"]
    print(
        f"source={meta['source_table']} eligible_rows={meta['eligible_rows']} "
        f"eligible_pasurams={meta['eligible_pasurams']} unique_padhams={meta['unique_padhams']}"
    )
    print(
        f"skipped_thaniyan={meta['skipped_thaniyan_rows']} "
        f"skipped_empty_or_note={meta['skipped_empty_or_note']} "
        f"skipped_excluded={meta.get('skipped_excluded_rows', 0)}"
    )
    print("Top 10 exact:")
    for i, row in enumerate(payload["corpus_exact"][:10], start=1):
        print(f"  {i:2d}. {row['token']!r} occ={row['occ']} pasurams={row['pasurams']}")
    print("Top clusters:")
    for i, row in enumerate(payload["corpus_clusters"][:10], start=1):
        print(
            f"  {i:2d}. {row['id']} {row['label_ta']} occ={row['occ']} pasurams={row['pasurams']}"
        )
    print(f"prabandham blocks: {len(payload['prabandhams'])}")
    print(f"alwar blocks: {len(payload['alwars'])}")
    print(
        "cross common="
        f"{len(payload['cross_alwar']['common_to_all_alwars'])} "
        f"unique_alwar={len(payload['cross_alwar']['unique_to_one_alwar'])} "
        f"unique_prabandham={len(payload['cross_alwar']['unique_to_one_prabandham'])}"
    )


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if config_path.name != "config.ini":
        raise SystemExit("POC only: use poc/config.ini (do not point this builder at test/prod)")

    clusters, stems, blocked = load_clusters(CLUSTERS_JSON)
    notes = load_json(NOTES_JSON) if NOTES_JSON.exists() else {}
    themes = load_theme_aliases(THEME_REGISTRY)
    seed = load_json(SEED_JSON)
    prabandham_rows = prabandham_order(seed)

    config = load_config(str(config_path))
    db = config.database
    if db.table != "PasuramsArthamTablePOC":
        raise SystemExit(f"Refusing table {db.table!r}; expected PasuramsArthamTablePOC")

    conn = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
    )
    cursor = conn.cursor(dictionary=True)
    try:
        payload = build_report(
            fetch_rows(cursor, db.table, args.batch_size),
            clusters,
            stems,
            blocked,
            notes,
            themes,
            prabandham_rows,
        )
    finally:
        cursor.close()
        conn.close()

    print_summary(payload)

    if args.dry_run and not args.apply:
        print("Dry-run: JSON not written. Use --apply to write public_html/data/padham_reports_poc.json")
        return
    if not args.apply:
        print("Use --apply to write public_html/data/padham_reports_poc.json")
        return

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    OUT_JSON.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} ({OUT_JSON.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
