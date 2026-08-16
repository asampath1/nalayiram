# AGENTS.md

## Cursor Cloud specific instructions

This repo powers **nalayiram.in** — a Tamil "Nalayira Divya Prabandham" padham-search website. It has two halves:

- **Web app**: PHP + MySQL under `public_html/` (search UI, JSON API, admin scripts).
- **Data pipeline**: Python 3 under `poc/` and `lookupsimilarwords/` (scrape → transliterate → themes → load MySQL → release notes).

The Cloud VM snapshot already has PHP 8.3, MariaDB 10.11, and the Python venv (`poc/.venv`) installed, plus local dev secrets created (see below). The update script only refreshes Python deps. Services are **not** auto-started — start them each session as below.

### Local dev DB (already provisioned in the snapshot)

- MariaDB database `nalayiram`, user `nalayiram` / password `nalayiram_dev` on `127.0.0.1:3306`.
- `public_html/database.php` and `poc/config.ini` are **gitignored** and already created pointing at this local DB. If missing (fresh clone without snapshot), recreate them: `database.php` defines a `$conn = new mysqli(...)`; `poc/config.ini` mirrors `poc/config.example.ini` with the `[db]` values above.
- The POC table (`PasuramsArthamTablePOC`) is seeded from the committed export `public_html/data.json` (10 pasurams, `முதல் திருவந்தாதி`). There is **no schema dump in the repo** — tables were created manually from the columns referenced in the PHP/loader code (`Sno, Prabandham, PasuramNumber, Pasuram, PattuNumber, Word, SimilarWords, Padham, Meaning, Alzwar, PadhamNumber, Title, NithyaanusandhamIndex, url` plus `DivyaDesamTable`, `SuggestedWords`, `DivyaPrabandhamCounts`, `DivyaDesamAlwarMatrix`).

### Start MariaDB (required before web app or pipeline)

MariaDB does not auto-start in the VM. Start it and wait a few seconds:

```bash
sudo mkdir -p /var/run/mysqld && sudo chown mysql:mysql /var/run/mysqld
(sudo mariadbd-safe >/tmp/mariadb.log 2>&1 &) ; sleep 8
mysql -u nalayiram -pnalayiram_dev nalayiram -e "SELECT 1;"
```

### Run the web app

```bash
cd public_html && php -S 0.0.0.0:8080
```

Then browse `http://localhost:8080/pocindex.php` (POC search). Search by padham/word, Alwar, Divyadesam, pasuram number (e.g. `2082`), or prabandham. `index.php` (prod table) and `test1.php` (UAT table) point at tables not seeded locally, so use `pocindex.php`. Rebuild autocomplete after loading data: `curl http://localhost:8080/update_suggested_words.php`.

### Data pipeline

```bash
# Load a JSON export/range into the POC table (idempotent within a range)
poc/.venv/bin/python poc/load_workbook.py --config poc/config.ini --input-json public_html/data.json
```

Scrapers (`poc/scrapers/`, `poc/orchestrate_poc.py`) hit external sites (dravidaveda.org, tidley) and need internet; the loader and tests run fully offline. See `poc/README.md` and `docs/PASURAM_INGESTION_PIPELINE.md` for the full workflow.

### Tests

`pytest` is not in `poc/requirements.txt`; the update script installs it. Run:

```bash
poc/.venv/bin/python -m pytest poc/test_merge_comment_rows.py poc/test_title_scrapers.py poc/test_transliterate.py lookupsimilarwords/test_pasuram_themes.py -q
```
