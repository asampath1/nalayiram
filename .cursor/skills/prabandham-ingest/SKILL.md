---
name: prabandham-ingest
description: End-to-end workflow for adding a new prabandham or pasuram range to the Nalayira Divya Prabandham site - scrape (tidley/dravidaveda/Excel), transliterate, themes, load POC DB, update counts, rebuild Kannadi release notes. Use when the user asks to ingest, scrape, add, or load a prabandham, pasuram range, padhaartham, or thaniyan, or to update release notes or counts after a data load.
---

# Prabandham Ingest Pipeline

Adds pasuram padham/meaning rows to the site DB and regenerates derived pages.
Full path-by-path reference: [docs/PASURAM_INGESTION_PIPELINE.md](../../../docs/PASURAM_INGESTION_PIPELINE.md).

## Ground rules

- **POC-first**: apply only to the POC table (`poc/config.ini` → `PasuramsArthamTablePOC`) unless the user explicitly asks for UAT/prod. Production DB loads are always manual (user's process).
- **Dry-run first**: never `--apply` before a dry-run whose counts the user's expectations match (pasuram count, padham rows, range).
- **Never touch thaniyans**: thaniyan rows are `PasuramNumber = 0` (PattuNumber = thaniyan index). Range deletes must not include 0.
- Run everything from the repo root with `poc/.venv/bin/python`.
- Confirm with the user before starting: prabandham name, PasuramNumber range, PattuNumber mapping, Alzwar, Title convention, source URLs/files, whether Divyadesam applies.

## Environments

| Env | Config | Table | Search UI | Kannadi release notes |
|-----|--------|-------|-----------|----------------------|
| POC | `poc/config.ini` | `PasuramsArthamTablePOC` | `pocindex.php` | `public_html/newreleasenotespoc.html` |
| UAT | `poc/config.test.ini` | `PasuramsArthamTableTest` | `test1.php` | `public_html/newreleasenotestest.html` |
| Prod | `poc/config.prod.ini` | `PasuramsArthamTable` | `index.php` | `public_html/newreleasenotes.html` |

## Workflow

```
Progress:
- [ ] 1. Scraper module (or reuse existing path)
- [ ] 2. Ingest dry-run + spot-check
- [ ] 3. Apply to POC DB + verify
- [ ] 4. Counts seed + reseed
- [ ] 5. V1_SPECS + rebuild release notes
```

**Step 1 — Scraper.** Pick the source path from the pipeline doc's checklist (dravidaveda scrape, Excel workbook, or tidley table-padham). For tidley table-padham prabandhams, copy an existing pair as template: `poc/scrapers/iramanusa_nootranthathi_tidley.py` + `poc/scrapers/ingest_iramanusa_nootranthathi.py` (multi-URL, mislabeled/missing verse handling, manual verse injection from a text file). Tidley pages have quirks — mislabeled verse numbers, missing verses, unnumbered verses, orphan பதவுரை tables. Surface every anomaly to the user instead of guessing.

**Step 2 — Dry-run.**

```bash
poc/.venv/bin/python poc/scrapers/ingest_<name>.py --config poc/config.ini --dry-run --no-themes
```

Check: section count = expected pasurams, padham row total sane, first/last/quirky verses correct. Review outputs: `poc/output/<name>_poc.json`, `lookupsimilarwords/reviews/<name>_*.csv`. (`--no-themes` speeds iteration; transliteration still calls OpenAI.)

**Step 3 — Apply + verify.**

```bash
poc/.venv/bin/python poc/scrapers/ingest_<name>.py --config poc/config.ini --apply
```

This deletes the range and reinserts. Then verify against the POC DB:

- distinct PasuramNumbers = expected count, range exact
- Alzwar/Prabandham values correct on sample rows
- thaniyan rows (`PasuramNumber=0`) unchanged
- duplicate check returns zero rows:

```sql
SELECT PasuramNumber, PadhamNumber, COUNT(*) FROM PasuramsArthamTablePOC
WHERE PasuramNumber BETWEEN <START> AND <END>
GROUP BY PasuramNumber, PadhamNumber HAVING COUNT(*) > 1;
```

**Step 4 — Counts.** Add/update the row in `public_html/divyaprabandham_counts_seed.json` (keep `sort_order` / `alwar_order` sequence), then:

```bash
poc/.venv/bin/python poc/scripts/seed_divyaprabandham_counts.py --config poc/config.ini --apply
```

**Step 5 — Release notes.** Add an entry to `V1_SPECS` in `poc/scripts/build_newreleasenote_poc_v1.py` (keep pasuram-number order; `kannadi_index` mode with `full_width` for 30+ pasurams). Rebuild:

```bash
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env poc
```

Only build `--env test` / `--env prod` when the user asks. If UAT/prod DBs don't have the data yet but the user wants the pages updated anyway, pass `--config poc/config.ini` so Kannadi openings render from POC data; links resolve after their manual DB load.

## Verify in UI

`pocindex.php?padhamPrefix=<prabandham name or pasuram number>` — Title shows green only when non-empty; PattuNumber in red; search uses `SimilarWords LIKE`.
