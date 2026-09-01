# Session resume — Path F, Kannadi release notes, பெரிய திருமொழி, Pasuram-Split

**Last updated:** 2026-09-01 (Pasuram-Split paused; UAT holds Acharya splits 1–12 and 13–222; next module is a new session)  
**Chat transcript (Path F):** [fd2690f1-8a21-4e0d-a304-04a085b687cc](file:///Users/anand/.cursor/projects/Users-anand-tensorflow-test-4K-IN-Site/agent-transcripts/fd2690f1-8a21-4e0d-a304-04a085b687cc/fd2690f1-8a21-4e0d-a304-04a085b687cc.jsonl)  
**Chat transcript (Periya Thirumozhi / Kannadi / counts / Pasuram-Split):** [5236674c-4fcc-48d1-9ab1-159202da6b98](file:///Users/anand/.cursor/projects/Users-anand-tensorflow-test-4K-IN-Site/agent-transcripts/5236674c-4fcc-48d1-9ab1-159202da6b98/5236674c-4fcc-48d1-9ab1-159202da6b98.jsonl)

Skill for splits: [`.cursor/skills/pasuram-split/SKILL.md`](../.cursor/skills/pasuram-split/SKILL.md)

Use this file after restarting Cursor to continue where we left off.

---

## Pasuram-Split (UAT) — paused 2026-08-28

**Purpose:** The words in the pasurams have been split, in order to make the meaning come out clear, and aid in recitation.

**Do not resume Acharya.org PDF loads.** Those splits differ from the user’s hardbound book. The user will scan and upload the book one batch at a time. Do not invent OCR until a scan arrives. Do not copy `PasuramWordsSplit` → `Pasuram`. Leave current UAT data in place.

### Where it lives

| Item | Detail |
|------|--------|
| Env | **UAT only** — `poc/config.test.ini`, table `PasuramsArthamTableTest`, UI `test1.php` |
| Column | `PasuramWordsSplit TEXT NULL` after `Pasuram` (same value on every padham row of a verse) |
| Search | Still `Pasuram` / `SimilarWords` — split column is display-only |
| UI | Side-by-side **Pasuram** and **Pasuram (split)** on `test1.php` |
| Recite twice | PDF/`**` → leading `● ` (U+25CF). Mid-verse `*` kept |

### Loaded on UAT (interim Acharya source)

| Work | PasuramNumber |
|------|----------------|
| திருப்பல்லாண்டு | **1–12** (`poc/input/0001-tpal-ta.pdf`, `thirupallandu_pasuram_words_split.txt`; `●` on 1, 2, 11, 12) |
| பெரியாழ்வார் திருமொழி முதல் பத்து | **13–117** (1-1 … 1-9; uneven pathigam lengths, not 10×10) |
| பெரியாழ்வார் திருமொழி இரண்டாம் பத்து | **118–222** (2-1 … 2-10) |

`Pasuram` was **not** changed. POC/prod tables were not loaded.

Mudhal Paththu map: 1-1 **13–22**, 1-2 **23–43** (21 verses), 1-3 **44–53**, 1-4 **54–63**, 1-5 **64–74**, 1-6 **75–85**, 1-7 **86–96**, 1-8 **97–107**, 1-9 **108–117**.

Irandam Paththu map: 2-1 **118–127**, 2-2 **128–138**, 2-3 **139–151**, 2-4 **152–161**, 2-5 **162–171**, 2-6 **172–181**, 2-7 **182–191**, 2-8 **192–201**, 2-9 **202–212**, 2-10 **213–222**.

Acharya Tamil PDFs: `https://acharya.org/dp/v3/1/02-perith10/{file}-ta.pdf` (Text page `?dp=1&Idx={first}.0&Text=y`). Early PDFs are TAB (`tab2unicode`); from Irandam Paththu they are Nirmala UI — ToUnicode swaps ெ/ப; `extract_acharya_words_split.py` uses TTF glyph ids + visual-order prefixes.

Apply (UAT only): `poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply --prabandham '…' --split-txt … --start N --end M`

Known one-off fixes: 1-4 verse **58** `தெளிவுறா`; 2-2 verse **128** `திருவுடைய`. Extra `●` when PDF had leading `**` (e.g. 1-5 verse 71, 2-6 verse 180). 2-10 has no leading `**` on first/last.

### Search (same long session; live on prod UI too)

Verse codes `3.1.1` / `3-1-1` / `3 1 1` are equivalent (digit-bounded `REGEXP`). English Alwar `Nammalwar` maps to நம்மாழ்வார். That search change was promoted to `pocindex.php`, `test1.php`, and `index.php`.

### Next for Pasuram-Split

Wait for scanned hardbound-book pages. Overlay UAT `PasuramWordsSplit` from the book when a file is provided.

---

## Weekend pause (2026-07-04) — resume Monday here

### Done this week

1. **முதல் திருவந்தாதி (பொய்கையாழ்வார்) — complete in POC (100/100)**
   - 2082–2091: already in DB
   - 2092–2116: Excel `Mudhalthiruvandhathi-2092-2116.xlsx` → themes + `Mudhal Thiruvandhathi` in SimilarWords
   - 2117–2181: Excel `Mudhalthiruvandhathi-remaining.xlsx` + tidley titles (`poc/title_scrapers/mudal_tidley.py`)
   - Titles for **2149** (pattu 68) and **2169** (pattu 88): user added manually in POC/UAT/Prod (tidley had no pages)
   - முதல் திருவந்தாதி range **(2082-2181)** on Kannadi release notes pages

2. **Kannadi release notes — two pages**

| File | Env | Search script |
|------|-----|---------------|
| `public_html/newreleasenotespoc.html` | POC | `pocindex.php` |
| `public_html/newreleasenotestest.html` | UAT / TEST | `test1.php` |
| `public_html/newreleasenotes.html` | Prod | `index.php` |

**Canonical layout:** Kannadi pasuram-number order + pathigam detail boxes (former v1).  
**Link catalog (not public):** `poc/data/release_notes_link_source.html`  
**Old pages removed:** `releasenotes*.html`, `*_v1.html`

**Regenerate per env:**

```bash
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env poc
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env test
poc/.venv/bin/python poc/scripts/build_newreleasenote_poc_v1.py --env prod
```

**v1 layout (current):**
- நித்யாநுஸந்தானம் unchanged
- Rest sorted by pasuram number, boxed by prabandham
- பெரியாழ்வார் / பெரிய திருமொழி / திருவாய்மொழி: **one box per pathigam** (pasuram list inside), grouped under patthu headings, 3 boxes per row
- நாச்சியார்: 14 patthu boxes, 3 per row (13–14 leave 3rd slot empty)
- One-line readability: `nowrap` + ellipsis on kannadi lines

3. **Build scripts**

| Script | Output |
|--------|--------|
| `poc/scripts/build_newreleasenote_poc_v1.py` | `newreleasenotespoc.html` / test / prod (`--env`) |
| `poc/title_scrapers/mudal_tidley.py` | Tidley titles for முதல் திருவந்தாதி |
| `poc/scripts/fill_mudal_remaining.py` | Excel + titles + themes → POC JSON |

4. **Pasuram 2043** (திருக்குறுந்தாண்டகம்): leading `—` in `Pasuram` column — Kannadi page skips it; user may still run SQL on POC/Test/Prod to strip dash for detail UI.

### Optional follow-ups

- [ ] Deploy HTML: `newreleasenotespoc.html` (+ counts seed / matrix refresh already on POC DB)
- [ ] **பெரிய திருமொழி மூன்றாம் பத்து (1148–1247)** — see workflow below
- [ ] Strip pasuram 2043 leading dash in DB if not done
- [ ] Git commit if desired (not done this session)

---

## பெரிய திருமொழி — இரண்டாம் பத்து DONE (POC, 2026-07-12)

| Item | Detail |
|------|--------|
| Range | **1048–1147** (100 pasurams, pathigams **2-1 … 2-10**) |
| Padham/Meaning source | **Dravidaveda** (`https://www.dravidaveda.org/{n}/`) — not other sites |
| Alwar | `திருமங்கையாழ்வார்` |
| Verse suffix | `–2-1-1` … `–2-10-10` (same UI style as first patthu `–1-4-1`) |
| Title | Per-pasuram Periyavachan Pillai avatharikai; format `(2-N–short) (DD)\n(commentary…)` |
| SimilarWords headings | e.g. `2-3–விற்பெருவிழவும்`, `2-3-Virperuvizhavum` (+ short Tamil/Eng) |
| Counts | பெரிய திருமொழி **200**; திருமங்கையாழ்வார் subtotal **253** |
| Release notes | POC section **இரண்டாம் பத்து (1048-1147)** with named boxes |

**Scripts / artifacts**

| Path | Role |
|------|------|
| `poc/scrapers/ingest_periya_thirumozhi_patthu2.py` | Scrape Dravidaveda → themes → POC JSON/DB |
| `poc/scripts/apply_periya_thirumozhi_patthu2_titles.py` | Parse `poc/pasuram.txt` → Title + heading aliases |
| `poc/pasuram.txt` | User title paste (from tidley நூறு page) |
| `poc/output/periya_thirumozhi_patthu2_*.json` | Scraped / POC / titles JSON |

**Do not** pull pathigam names or titles from random web sources. Prefer Dravidaveda for padhamurai; Titles from the tidley **நூறு** page (below) + DD names from user.

---

## Title workflow for each பத்து (100s) — for 3rd பத்து onward

Titles for an entire patthu (100 pasurams) come from **one tidley “நூறு” page** (Periyavachan Pillai avatharikai தொகுப்பு), not from 10 separate pathigam pages.

**Example (இரண்டாம் நூறு — already applied):**  
https://tidley.com/2019/06/15/ஸ்ரீ-பெரிய-திருமொழியில்-6/

**Page pattern (understood):**
1. Pathigams separated by `————————`
2. Each pathigam starts with the **mudhal pasuram** line ending in `–2-N-1-` (or `3-N-1-`, etc.) — that opening is the short name source (e.g. வானவர் / காசையாடை / விற்பெருவிழவும்)
3. Then **10 commentary blocks**, ending with `முதல்` … `பத்தாம் பாசுரத்தில்` (last block may omit the marker)
4. Title stored as: `(P-N–shortName) (DivyaDesamName)\n(commentary)`
5. SimilarWords also get `P-N–shortName` + English `P-N-Translit`

**What user supplies each time:**
- Paste / file of that நூறு page content (or confirm scrape from that tidley URL only)
- **DivyaDesam names** per pathigam (திருவேங்கடம், திருவல்லிக்கேணி, …) — agent does **not** invent DD names

**Next:** மூன்றாம் பத்து **1148–1247** (3-1 … 3-10) — padhamurai via Dravidaveda when ready; Titles from the matching **மூன்றாம் நூறு** tidley page + DD list from user.

---

## What we built (Path F — tidley table ingest)

| PasuramNumber | Prabandham | Pattus | Scraper | Ingest CLI |
|---------------|------------|--------|---------|------------|
| 2672 | திருவெழுகூற்றிருக்கை | 10 | `poc/scrapers/thiruvozhukootrirukkai_tidley.py` | `ingest_thiruvozhukootrirukkai.py` |
| 2673 | சிறிய திருமடல் | 16 | `poc/scrapers/siriya_thirumadal_tidley.py` | `ingest_siriya_thirumadal.py` |
| 2674 | பெரிய திருமடல் | 31 (2 URLs) | `poc/scrapers/periya_thirumadal_tidley.py` | `ingest_periya_thirumadal.py` |

**2673:** Pasuram text from `poc/input/siriya_thirumadal_pattus.txt`; titles empty.  
**2674:** Pasuram = paragraph immediately above **பதவுரை** on tidley (2 pages); titles empty.  
**Alzwar:** 2673 ingest uses `Thirumangai Alwar`; 2672/2674 use `திருமங்கை ஆழ்வார்`.

---

## Theme / search fixes (ingest → `SimilarWords`, not PHP)

1. **Vamana detector** — `lookupsimilarwords/detectors/vamanan_detector.json`  
   Added stems: `அளப்ப`, `அளக்க`, `அடி அள`.

2. **Pasuram in theme checks** — `lookupsimilarwords/pasuram_themes.py`  
   Theme detection scans **Pasuram** text as well as Padham + Meaning.

3. **Per-pattu themes** — `group_by_pasuram_number=False` in 2672/2673/2674 ingest scripts  
   (default grouping is `(PasuramNumber, PattuNumber)`).

4. **Thaniyan search** — `poc/scripts/link_thaniyan_similar_words.py`  
   Appends parent prabandham names to thaniyan `SimilarWords`  
   (சிறிய/பெரிய திருமடல், திருவெழுகூற்றிருக்கை, திரு நெடும் தாண்டகம்).

5. **Search** works via existing PHP + **`SimilarWords LIKE`** — no PHP change required if DB is correct.

---

## Database load status

| Table | 2672 | 2673 | 2674 | Thaniyan `SimilarWords` link |
|-------|------|------|------|-------------------------------|
| `PasuramsArthamTablePOC` | 119 rows | 244 rows | 522 rows | Done (55 rows) |
| `PasuramsArthamTableTest` | 119 rows | 244 rows | **You: manual** | Done (55 rows) |
| `PasuramsArthamTable` (Prod) | 119 rows | 244 rows | **You: manual** | Done (55 rows) |

### Commands to (re)load

```bash
cd /Users/anand/tensorflow-test/4K-IN-Site

# POC
poc/.venv/bin/python poc/scrapers/ingest_thiruvozhukootrirukkai.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scrapers/ingest_siriya_thirumadal.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumadal.py --config poc/config.ini --apply
poc/.venv/bin/python poc/scripts/link_thaniyan_similar_words.py --config poc/config.ini

# UAT
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumadal.py --config poc/config.test.ini --apply
poc/.venv/bin/python poc/scripts/link_thaniyan_similar_words.py --config poc/config.test.ini

# Prod
poc/.venv/bin/python poc/scrapers/ingest_periya_thirumadal.py --config poc/config.prod.ini --apply
poc/.venv/bin/python poc/scripts/link_thaniyan_similar_words.py --config poc/config.prod.ini
```

Configs: `poc/config.ini` (POC), `poc/config.test.ini` (UAT), `poc/config.prod.ini` (Prod).

---

## Release notes (deploy HTML to server)

| File | UI |
|------|-----|
| `public_html/newreleasenotespoc.html` | pocindex.php |
| `public_html/newreleasenotestest.html` | test1.php |
| `public_html/newreleasenotes.html` | index.php |

---

## Key output / review files

- `poc/output/thiruvozhukootrirukkai_poc.json`
- `poc/output/siriya_thirumadal_poc.json`
- `poc/output/periya_thirumadal_poc.json`
- `lookupsimilarwords/reviews/thiruvozhukootrirukkai_tidley.csv`
- `lookupsimilarwords/reviews/siriya_thirumadal_tidley.csv`
- `lookupsimilarwords/reviews/periya_thirumadal_tidley.csv`

---

## Docs updated

- `docs/PASURAM_INGESTION_PIPELINE.md` — Path F + 2673/2674 section
- `poc/README.md` — Path F commands
- `lookupsimilarwords/test_pasuram_themes.py` — pattu-6 vamana + per-pattu grouping tests

---

## Verify on site

- POC: https://nalayiram.in/pocindex.php?padhamPrefix=vamanan  
- POC 2674: https://nalayiram.in/pocindex.php?padhamPrefix=2674  
- Search `சிறிய திருமடல்` → 18 blocks (2 thaniyan + 16 pattus) when DB + SimilarWords are correct

**2673 Vamana pattus:** 6, 9  
**2674 Vamana pattus (POC sample):** 1, 21, 25  

---

## SQL — Āzhvār × Prabandham Vamana counts

```sql
SELECT
    Alzwar,
    Prabandham,
    COUNT(DISTINCT CONCAT(COALESCE(PasuramNumber, ''), '|', COALESCE(PattuNumber, ''))) AS vamana_pattu_blocks,
    COUNT(*) AS vamana_padham_rows
FROM PasuramsArthamTablePOC   -- swap: PasuramsArthamTableTest / PasuramsArthamTable
WHERE SimilarWords LIKE '%vamanan%'
   OR SimilarWords LIKE '%thiruvikraman%'
   OR SimilarWords LIKE '%வாமனன்%'
   OR SimilarWords LIKE '%திருவிக்ரமன்%'
GROUP BY Alzwar, Prabandham
ORDER BY Alzwar, Prabandham;
```

---

## பெரிய திருமொழி POC progress

| Done | PasuramNumber | Pathigam / notes |
|------|---------------|------------------|
| Yes | 948–1047 | முதல் பத்து 1-1 … 1-10 (tidley padhamurai) |
| Yes | 1048–1147 | இரண்டாம் பத்து 2-1 … 2-10 (Dravidaveda + tidley நூறு Titles) |
| Yes | 1148–1247 | மூன்றாம் பத்து 3-1 … 3-10 (Dravidaveda + `pasuram.txt` Titles) |
| Yes | 1248–1347 | நான்காம் பத்து 4-1 … 4-10 (97/100 Dravidaveda; 1330–1332 backfilled manually 2026-08-17) |
| Yes | 1348–1447 | ஐந்தாம் பத்து 5-1 … 5-10 (all Dravidaveda; 5-9-1…5 empty Title) |
| Yes | 1448–1547 | ஆறாம் பத்து 6-1 … 6-10 (99/100 Dravidaveda; **1485** stub only) |
| Yes | 1548–1647 | ஏழாம் பத்து 7-1 … 7-10 (100/100 Dravidaveda; 7-10 numeric scrape) |
| Yes | 1648–1747 | எட்டாம் பத்து 8-1 … 8-10 (100/100 Dravidaveda, all direct numeric) |
| Yes | **1748–1847** | **ஒன்பதாம் பத்து 9-1 … 9-10** (100/100 Dravidaveda, all direct numeric) |
| Yes | **1848–1951** | **பத்தாம் பத்து 10-1 … 10-10** (104/104 Dravidaveda; **10-7 is 14 verses** 1908–1921) |
| Yes | **1952–2031** | **பதினொன்றாம் பத்து 11-1 … 11-8** (80/80 Dravidaveda; no 11-9/11-10) |

பெரிய திருமொழி **ends at 2031**. Next prabandham in sequence is **திருக்குறுந்தாண்டகம் (2032–)**.

**Title author string:** `(ஸ்ரீ பெரியவாச்சான் பிள்ளை)` in Titles for **948–2031** (1st–11th பத்து).

**POC counts (பெரிய திருமொழி):** **1084** pasurams loaded — patthus 1–11 complete, no gaps in 948–2031. திருமங்கையாழ்வார் `alwar_subtotal` **1137**; counts footer **4058**.

**1330–1332 backfill (2026-08-17):** the long-standing patthu 4 gap (4-9-3…4-9-5, திருவிந்தளூர்) is
closed in POC. Dravidaveda still 404s on these three, so verse, padhavurai and Title came from a
manual block in `poc/pasuram.txt` via `poc/scrapers/ingest_periya_thirumozhi_1330_1332.py` — the
first non-Dravidaveda padhavurai in this prabandham. **Padhavurai is partial** (4/4/5 padham rows
vs 7–13 for neighbours); uncovered verse words are listed in
`lookupsimilarwords/reviews/periya_thirumozhi_1330_1332_padhavurai_coverage.txt`.
1331 and 1332 are stored as single-line verses (supplied that way); every other pasuram is 4 lines.

**பத்தாம் + பதினொன்றாம் பத்து notes (2026-08-18):**
- **No category crawl needed** — `dravidaveda.org/{n}/` served padhavurai for all 184 pasurams
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu10.py` (104 pasurams, 1374 padham rows) and `patthu11.py` (80 pasurams, 1121 padham rows); all themes; no stubs
- Titles: `apply_periya_thirumozhi_patthu10_titles.py` / `patthu11`; Pasuram: `replace_periya_thirumozhi_patthu10_pasuram_from_txt.py` / `patthu11`
- **Do not use modulo-10 from 1848** — 10-7’s extra 4 verses (1908–1921 = 14) shift every later pathigam. Use explicit `PATHIGAMS` ranges. `PattuNumber` = verse-within-pathigam (1–14 for 10-7)
- **Sparse Divyadesam mapping** — do not invent `DivyaDesamTable` rows. Only 13 of 104 (patthu 10) and 14 of 80 (patthu 11) were already mapped; the matrix only reflects those cells. 10-1 already has the 18 DDs for பதினெண் திருப்பதிகள்
- Omit Divyadesam Title bracket when the Title section has none (10-4…10-8, 10-10, 11-1…11-4, 11-6…11-8). Keep second-bracket *as written* even when not a DD (10-1 பதினெண் திருப்பதிகள், 10-2 பொங்கத்தம் பொங்கோ, 10-3 குழமணி தூரம், 10-9 பழமொழியால்…, 11-5 திருச்சாழல்)
- Short names as written in Title section: **10-4 `சந்தமலர் க்குழல்`**, **11-1 `குன்றமொன்`** (not the verse spellings)
- `poc/pasuram.txt` **duplicates all of patthu 11** (~lines 346–585 and 587–826). Parsers use the first copy and cut at the second `11-1-1` `verse_block_start` (cutting at `match.start()` leaked the duplicate verse into 11-8-10 commentary). Also cut at `Title :`. Patthu 10 extract window stops at first `11-1-1`
- Suffix regex is **EOL-anchored** so 10-6-1 commentary quoting `திருவாய்மொழி -10-8-2-` is ignored. Verse numbers allow **1–14** for patthu 10
- Release notes: `periya_thirumozhi` V1_SPECS / `classify_entries` to **2031**; 18 pathigam links; POC only (UAT/Prod after user verifies). Kannadi 10-7 box shows 14 openings

**ஒன்பதாம் பத்து notes (2026-08-16):**
- **No category crawl needed** — dravidaveda serves this patthu at `/{n}/` for all 100 pasurams
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu9.py` — 100 pasurams, 1567 padham rows, all themes
- Titles: `poc/scripts/apply_periya_thirumozhi_patthu9_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu9_pasuram_from_txt.py`
- **First patthu spanning many Divyadesams** (patthus 6–8 were single-DD): கண்ணங்குடி, நாகை, புல்லாணி 1–2, குறுங்குடி 1–2, வல்லவாழ், மாலிருஞ்சோலை 1–2, கோட்டியூர்
- Title header carries a context bracket only for 9-2…9-5 and 9-9
- No short-name collisions with existing pathigams; `9-10 எங்கள்`, `9-8 முந்துற`, `9-9 மூவரில்`, `9-4 காவார்` are common words, so prefer the prefixed alias when searching
- `DivyaDesamTable` already mapped 1748–1847, so only the matrix needed refreshing
- Themes: 7 of 9 matched across 56 pasurams (patthu 8 was 57 — comparable)
- Release notes: `periya_thirumozhi` V1_SPECS to **1847**; POC only (UAT/Prod after user verifies)

**எட்டாம் பத்து notes (2026-08-16):**
- **No category crawl needed** — dravidaveda serves this patthu at `/{n}/` for all 100 pasurams
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu8.py` — 100 pasurams, 1508 padham rows, all themes
- Titles: `poc/scripts/apply_periya_thirumozhi_patthu8_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu8_pasuram_from_txt.py`
- All 10 pathigams are திரு கண்ணபுரம் 1…10 — pathigam ordinals at the same Divyadesam
- Title header carries a context bracket only for 8-1…8-4 (pasuram.txt supplies none for 8-5…8-10)
- **8-5 short name `தந்தை காலில்` duplicates 7-5** — user accepted; bare-term search returns both pathigams (20)
- `DivyaDesamTable` already mapped 1648–1747, so only the matrix needed refreshing
- Release notes: `periya_thirumozhi` V1_SPECS to **1747**; POC only (UAT/Prod after user verifies)

**ஏழாம் பத்து notes (2026-08-13):**
- Crawl: `poc/scrapers/dravidaveda_periya_thirumozhi_patthu7_crawl.py` (7-1…7-9 category → விளக்க உரை)
- Numeric: 7-10 (1638–1647) via `dravidaveda.org/{n}/`
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu7.py` — 100 pasurams, 1564 padham rows, all themes
- Titles: `poc/scripts/apply_periya_thirumozhi_patthu7_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu7_pasuram_from_txt.py`
- திரு நறையூர் 8/9/10 in Titles are pathigam ordinals at the same Divyadesam
- Release notes: `periya_thirumozhi` V1_SPECS to **1647**; POC only (UAT/Prod after user verifies)

**ஆறாம் பத்து notes (2026-08-10):**
- Crawl: `poc/scrapers/dravidaveda_periya_thirumozhi_patthu6_crawl.py` (category → pathigam → விளக்க உரை)
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu6.py` — 100 pasurams, 1294 padham rows, all themes
- Titles: `poc/scripts/apply_periya_thirumozhi_patthu6_titles.py`; Pasuram: `replace_periya_thirumozhi_patthu6_pasuram_from_txt.py`
- **Flag:** pasuram **1485** (6-4-8) — no padhavurai on Dravidaveda (`1-96/`); verse-only stub from `pasuram.txt`
- Release notes: `periya_thirumozhi` V1_SPECS to **1547**; 10 pathigam links in `release_notes_link_source.html`
- Pathigam alias example: `6-1 வண்டுணும்` (exceptional short name vs verse `வண்டுண்`)

**மூன்றாம் பத்து notes (2026-07-13):**
- Ingest: `poc/scrapers/ingest_periya_thirumozhi_patthu3.py` — 100 pasurams, 1028 padham rows
- Titles: `poc/scripts/apply_periya_thirumozhi_patthu3_titles.py` (format includes DD + author)
- **Flag:** pasuram **1246** (3-10-9) has **no commentary** in `pasuram.txt` (verse only) — Title header present with empty `()`

**முதல் திருவந்தாதி:** **Complete** (2082–2181) in POC; UAT/Prod titles for 2149/2169 done by user.

---

## Pending / resume checklist

- [ ] Deploy `newreleasenotespoc.html` (பத்து 10–11 / 1848–2031) if not uploaded
- [ ] After POC verify: rebuild UAT/Prod release notes (`--env test` / `--env prod` with `--config poc/config.ini`)
- [ ] Backfill padhavurai for **1485** (6-4-8) if Dravidaveda fixes `1-96/`
- [ ] Pasuram 2043: strip leading `—` in Pasuram column (POC/Test/Prod) if not done
- [ ] Manual UAT/Prod load for patthus 6–11 when ready
- [ ] Git commit if desired

---

## SEO — prabandham landing pages (prod)

- Goal: rank for **prabandham names** (e.g. பெரிய திருமொழி, Thiruppavai), not every pasuram/pathigam.
- `public_html/seo_prabandhams.php` + dynamic title/description/canonical on `index.php` when search matches a known prabandham (Tamil or English alias → Tamil search).
- Sitemap: `poc/scripts/build_sitemap.py` → `public_html/sitemap.xml` (hubs + 27 prabandham `padhamPrefix` URLs only).
- QA smoke (HTTP/title/canonical): `poc/.venv/bin/python poc/scripts/smoke_seo_prabandham_urls.py` (+ `--english-aliases`); report `poc/output/seo_prabandham_smoke.csv`.
- Search-field combos (padham / Āzhvār / Divyadesam): `poc/.venv/bin/python poc/scripts/smoke_search_combos.py`; report `poc/output/search_combos_smoke.csv`.
- After upload: resubmit sitemap in Google Search Console.

1. Open this file: `docs/SESSION_RESUME.md`
2. Say: *“Continue from SESSION_RESUME.md — [your next task]”*
3. Or reference chat transcript: `5236674c-4fcc-48d1-9ab1-159202da6b98`
