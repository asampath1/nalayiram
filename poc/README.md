# POC: Tamil Pasuram Automation

This folder contains the POC pipeline code for scraping, transliterating and loading Pasurams into MySQL. Files in this folder are intentionally kept outside `public_html`.

**Full end-to-end guide (scrape → themes → titles → load → release notes → website upload):** [docs/PASURAM_INGESTION_PIPELINE.md](../docs/PASURAM_INGESTION_PIPELINE.md) — start with the **[New prabandham checklist](../docs/PASURAM_INGESTION_PIPELINE.md#new-prabandham-checklist)**.

**UAT load and checklist:** [poc/UAT_THIRUVANDHATHI.md](UAT_THIRUVANDHATHI.md) — uses [poc/config.test.ini](config.test.ini) (`PasuramsArthamTableTest`).

## Quick start (scrape → load)

1. Install Python 3.8+ and use `poc/.venv` when available.
2. Copy [poc/config.example.ini](config.example.ini) to `poc/config.ini` (and `poc/config.test.ini` for UAT).
3. Run the full scrape pipeline:

```bash
poc/.venv/bin/python -m poc.orchestrate_poc --config poc/config.ini --output poc/output/pasurams_poc.json
```

4. Load a range (always prefer `--replace-range` to avoid duplicates):

```bash
poc/.venv/bin/python poc/load_workbook.py --config poc/config.ini \
  --input-json poc/output/pasurams_poc.json --replace-range <START> <END>
```

## Title scrapers (`poc/title_scrapers/`)

Update **`Title`** on existing DB rows without reloading padham lines.

| Script | Purpose |
|--------|---------|
| [apply_titles_from_excel.py](title_scrapers/apply_titles_from_excel.py) | Commentary from `*-commentary.xlsx` workbooks |
| [append_neerattam_vilakku.py](title_scrapers/append_neerattam_vilakku.py) | Periyazhvar vilakku urai from tidley → `(section) - text` |
| [apply_titles.py](title_scrapers/apply_titles.py) | Thiruvandhathi titles from tidley (`nanmugan`, `irandam`, `moondram`) |

Examples:

```bash
# Excel commentary (Title column)
poc/.venv/bin/python poc/title_scrapers/apply_titles_from_excel.py \
  --xlsx thirupalliyezhuchi-commentary.xlsx --config poc/config.ini --apply

# Periyazhvar vilakku (152-161, 182-201, 192-201, 463-473)
poc/.venv/bin/python poc/title_scrapers/append_neerattam_vilakku.py \
  --section neerattam --config poc/config.ini --apply

# Thiruvandhathi tidley titles
poc/.venv/bin/python poc/title_scrapers/apply_titles.py \
  --prabandham irandam --config poc/config.ini --apply
```

Shared parsing: [title_scrapers/tidley.py](title_scrapers/tidley.py), [title_scrapers/periyazhvar_vilakku_tidley.py](title_scrapers/periyazhvar_vilakku_tidley.py).

## Tidley table padham (`poc/scrapers/`)

**Path F** — full padham load from tidley HTML tables (e.g. திருவெழுகூற்றிருக்கை 2672, சிறிய திருமடல் 2673, பெரிய திருமடல் 2674):

```bash
poc/.venv/bin/python poc/scrapers/ingest_thiruvozhukootrirukkai.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scrapers/ingest_siriya_thirumadal.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumadal.py --config poc/config.ini --apply
```

See [docs/PASURAM_INGESTION_PIPELINE.md §7](../docs/PASURAM_INGESTION_PIPELINE.md#7-path-f--tidley-table-padham-thiruvozhukootrirukkai).

## Core pipeline files

- `poc/scraper_adapter.py` — normalize scraper output into JSON
- `poc/transliterate_wrapper.py` — transliteration + cache logic
- `poc/transliterate_gpt_adapter.py` — optional adapter for `public_html/transliterateGPT.py`
- `poc/fill_workbook.py` — Excel Thiruvandhathi fill (Word, SimilarWords, themes)
- `poc/load_workbook.py` / `poc/db_loader.py` — load JSON into MySQL
- `poc/config.example.ini` — sample configuration

## Themes

Theme detectors and range apply live under `lookupsimilarwords/`. See [lookupsimilarwords/README.md](../lookupsimilarwords/README.md).
