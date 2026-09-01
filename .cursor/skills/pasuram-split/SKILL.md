---
name: pasuram-split
description: >-
  Pasuram-Split project for Nalayiram.in — the words in the pasurams have been
  split, in order to make the meaning come out clear, and aid in recitation.
  Use when the user names Pasuram-Split, pasuram split, word split, padham
  split, recitation splits, or PadhaArtham word breaks; not for prabandham
  ingest unless they also ask to split verse words.
---

# Pasuram-Split project

The words in the pasurams have been split, in order to make the meaning come out clear, and aid in recitation.

This is a **named workstream** on the Nalayira Divya Prabandham site ([nalayiram.in](https://nalayiram.in)).

**Paused (2026-08-28):** Acharya.org Tamil PDF iteration is **stopped**. Those PDFs split differently from the user’s hardbound book (the intended source). Leave current UAT `PasuramWordsSplit` in place. Do **not** load 3rd paththu or further Acharya PDFs. Do **not** copy split → `Pasuram`. The user will scan and upload the book **one batch at a time** — wait for that file; do not invent an OCR pipeline until they provide it.

## When this skill applies

- User says **Pasuram-Split**, **pasuram split**, word/padham split, or recitation-oriented splitting.
- Work that changes how a verse is broken into `Padham` / `Word` lines vs the full `Pasuram` text.

Ingesting a new prabandham range is a different skill: [prabandham-ingest](../prabandham-ingest/SKILL.md).

## Ground rules

- **This workstream is UAT-first** until the user says otherwise: `PasuramsArthamTableTest` via `poc/config.test.ini`, UI `test1.php`.
- Ingest and other site work stay **POC-first** (`PasuramsArthamTablePOC`). Do not load or edit the live prod table unless asked.
- **Do not change prod UI** (`index.php`) unless asked. Site is live.
- Run Python from repo root with `poc/.venv/bin/python`.
- Dry-run before `--apply`. Never delete thaniyans (`PasuramNumber = 0`) as a side effect of a pasuram-range replace.
- Confirm prabandham, PasuramNumber range, and whether splits are display-only or DB `Padham`/`Word` rows before writing data.

## Recitation split column

`PasuramWordsSplit` is a TEXT column **on UAT only** (`PasuramsArthamTableTest`, after `Pasuram`). Same value on every padham row of a verse. Existing `Pasuram` is left unchanged until the user validates and asks to copy.

- Keep PDF `*` recitation markers. Drop PDF verse numbers; display uses table `PasuramNumber`.
- PDF leading `**` (recite twice) is stored as a leading `● ` (U+25CF). Mid-verse `*` stays `*`.
- Search still uses `Pasuram` / `SimilarWords`, not the new column.
- UAT UI [`test1.php`](../../../public_html/test1.php) shows **Pasuram** and **Pasuram (split)** side by side. Empty split cells for other prabandhams.

Acharya Tamil PDFs are TAB-encoded. Extract:

```bash
poc/.venv/bin/python poc/scripts/extract_acharya_words_split.py \
  --pdf poc/input/<file>-ta.pdf --out poc/input/<name>_pasuram_words_split.txt \
  --start-marker '<first verse opening>' --pdf-count N --pasuram-start <DB number>
```

### Thirupallandu (1–12)

Source: [`poc/input/0001-tpal-ta.pdf`](../../../poc/input/0001-tpal-ta.pdf). Split txt: [`poc/input/thirupallandu_pasuram_words_split.txt`](../../../poc/input/thirupallandu_pasuram_words_split.txt). `●` on 1, 2, 11, 12.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --dry-run
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply
```

### பெரியாழ்வார் திருமொழி 1-1 வண்ண மாடங்கள் (13–22)

Source: [`poc/input/0013-vm-ta.pdf`](../../../poc/input/0013-vm-ta.pdf) from [acharya.org Tamil](https://acharya.org/dp/v3/1/02-perith10/0013-vm-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_1_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_1_pasuram_words_split.txt). `●` on 13 and 22.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_1_pasuram_words_split.txt \
  --start 13 --end 22
```

Mudhal Paththu is 9 pathigam PDFs (13–117), not 100 even verses.

### பெரியாழ்வார் திருமொழி 1-2 சீதக்கடல் (23–43)

Source: [`poc/input/0023-sk-ta.pdf`](../../../poc/input/0023-sk-ta.pdf) from [acharya.org Tamil](https://acharya.org/dp/v3/1/02-perith10/0023-sk-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_2_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_2_pasuram_words_split.txt). `●` on 23 and 43 (21 verses).

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_2_pasuram_words_split.txt \
  --start 23 --end 43
```

### பெரியாழ்வார் திருமொழி 1-3 மாணிக்கம் கட்டி (44–53)

Source: [`poc/input/0044-mk-ta.pdf`](../../../poc/input/0044-mk-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_3_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_3_pasuram_words_split.txt). `●` on 44 and 53.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_3_pasuram_words_split.txt \
  --start 44 --end 53
```

### பெரியாழ்வார் திருமொழி 1-4 தன் முகத்து (54–63)

Source: [`poc/input/0054-tm-ta.pdf`](../../../poc/input/0054-tm-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_4_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_4_pasuram_words_split.txt). `●` on 54 and 63. TAB leftover `தௌ¤வுறா` on verse 58 is stored as **தெளிவுறா**.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_4_pasuram_words_split.txt \
  --start 54 --end 63
```

### பெரியாழ்வார் திருமொழி 1-5 உய்யவுலகு (64–74)

Source: [`poc/input/0064-uu-ta.pdf`](../../../poc/input/0064-uu-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_5_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_5_pasuram_words_split.txt). `●` on 64, 71, and 74 (PDF leading `**` on verse 8).

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_5_pasuram_words_split.txt \
  --start 64 --end 74
```

### பெரியாழ்வார் திருமொழி 1-6 மாணிக்கக்கிண்கிணி (75–85)

Source: [`poc/input/0075-mk-ta.pdf`](../../../poc/input/0075-mk-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_6_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_6_pasuram_words_split.txt). `●` on 75 and 85.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_6_pasuram_words_split.txt \
  --start 75 --end 85
```

### பெரியாழ்வார் திருமொழி 1-7 தொடர்சங்கிலிகை (86–96)

Source: [`poc/input/0086-ts-ta.pdf`](../../../poc/input/0086-ts-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_7_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_7_pasuram_words_split.txt). `●` on 86 and 96.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_7_pasuram_words_split.txt \
  --start 86 --end 96
```

### பெரியாழ்வார் திருமொழி 1-8 பொன்னியல் (97–107)

Source: [`poc/input/0097-pi-ta.pdf`](../../../poc/input/0097-pi-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_8_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_8_pasuram_words_split.txt). `●` on 97 and 107.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_8_pasuram_words_split.txt \
  --start 97 --end 107
```

### பெரியாழ்வார் திருமொழி 1-9 வட்டு நடுவே (108–117)

Source: [`poc/input/0108-vn-ta.pdf`](../../../poc/input/0108-vn-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_1_9_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_1_9_pasuram_words_split.txt). `●` on 108 and 117.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_1_9_pasuram_words_split.txt \
  --start 108 --end 117
```

Mudhal Paththu (1-1 … 1-9, pasurams **13–117**) is complete on UAT.

Later Acharya Tamil PDFs (from Irandam Paththu) embed Nirmala UI instead of TAB. `pdftotext` ToUnicode swaps ெ/ப; extract uses TTF glyph ids + visual-order ெ/ே/ை → logical, then NFC.

### பெரியாழ்வார் திருமொழி 2-1 மெச்சூது (118–127)

Source: [`poc/input/0118-mu-ta.pdf`](../../../poc/input/0118-mu-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_1_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_1_pasuram_words_split.txt). `●` on 118 and 127.

```bash
poc/.venv/bin/python poc/scripts/apply_thirupallandu_words_split.py --apply \
  --prabandham 'பெரியாழ்வார் திருமொழி' \
  --split-txt poc/input/periyazhwar_tm_2_1_pasuram_words_split.txt \
  --start 118 --end 127
```

### பெரியாழ்வார் திருமொழி 2-2 அரவணையாய் (128–138)

Source: [`poc/input/0128-aa-ta.pdf`](../../../poc/input/0128-aa-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_2_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_2_pasuram_words_split.txt). `●` on 128 and 138. Manual fix: verse 128 `திருவுடைய`.

### பெரியாழ்வார் திருமொழி 2-3 போய்ப்பாடு (139–151)

Source: [`poc/input/0139-pp-ta.pdf`](../../../poc/input/0139-pp-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_3_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_3_pasuram_words_split.txt). `●` on 139 and 151 (13 verses).

### பெரியாழ்வார் திருமொழி 2-4 நீராட்டம் (152–161)

Source: [`poc/input/0152-va-ta.pdf`](../../../poc/input/0152-va-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_4_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_4_pasuram_words_split.txt). `●` on 152 and 161.

### பெரியாழ்வார் திருமொழி 2-5 பின்னைமணாளனை (162–171)

Source: [`poc/input/0162-pm-ta.pdf`](../../../poc/input/0162-pm-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_5_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_5_pasuram_words_split.txt). `●` on 162 and 171.

### பெரியாழ்வார் திருமொழி 2-6 வேலிக்கோல் (172–181)

Source: [`poc/input/0172-vk-ta.pdf`](../../../poc/input/0172-vk-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_6_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_6_pasuram_words_split.txt). `●` on 172, 180, and 181 (PDF leading `**` on verse 9).

### பெரியாழ்வார் திருமொழி 2-7 பூச்சூடல் (182–191)

Source: [`poc/input/0182-am-ta.pdf`](../../../poc/input/0182-am-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_7_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_7_pasuram_words_split.txt). `●` on 182 and 191.

### பெரியாழ்வார் திருமொழி 2-8 காப்பிடல் (192–201)

Source: [`poc/input/0192-ip-ta.pdf`](../../../poc/input/0192-ip-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_8_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_8_pasuram_words_split.txt). `●` on 192 and 201.

### பெரியாழ்வார் திருமொழி 2-9 வெண்ணெய்விழுங்கி (202–212)

Source: [`poc/input/0202-vv-ta.pdf`](../../../poc/input/0202-vv-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_9_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_9_pasuram_words_split.txt). `●` on 202 and 212 (11 verses).

### பெரியாழ்வார் திருமொழி 2-10 ஆற்றிலிருந்து (213–222)

Source: [`poc/input/0213-ai-ta.pdf`](../../../poc/input/0213-ai-ta.pdf). Split txt: [`poc/input/periyazhwar_tm_2_10_pasuram_words_split.txt`](../../../poc/input/periyazhwar_tm_2_10_pasuram_words_split.txt). No leading `**` on first or last verse in the PDF.

Irandam Paththu (2-1 … 2-10, pasurams **118–222**) is loaded on UAT from Acharya PDFs (interim). **Do not continue to 3rd paththu from Acharya.**

**Next:** wait for the user’s scanned hardbound-book pages (one upload at a time). Replace or overlay UAT splits from that book when they provide a file. Copy split → `Pasuram` only after they validate.

## Nalayiram context this agent must keep

Site: Nalayira Divya Prabandham PadhaArtham search. Shared Hostinger DB `u868488353_tamildb`.

| Env | Config | Pasuram table | Search UI | Kannadi |
|-----|--------|---------------|-----------|---------|
| POC | `poc/config.ini` | `PasuramsArthamTablePOC` | `pocindex.php` | `newreleasenotespoc.html` |
| UAT | `poc/config.test.ini` | `PasuramsArthamTableTest` | `test1.php` | `newreleasenotestest.html` |
| Prod | `poc/config.prod.ini` | `PasuramsArthamTable` | `index.php` | `newreleasenotes.html` |

Shared (not env-copied pasuram tables): `DivyaDesamTable`, `SuggestedWords`, `DivyaDesamAlwarMatrix`.

Search UI: three boxes (padham/word/number **and/or** Alwar **and/or** Divyadesam). Verse codes `3.1.1` / `3-1-1` / `3 1 1` are equivalent in search (digit-bounded). Autocomplete Alwar `Nammalwar-நம்மாழ்வார்` uses the Tamil part; English-only `Nammalwar` maps to நம்மாழ்வார்.

### How split words live in the DB today

One **pasuram** is many **padham rows** (same `PasuramNumber`, increasing `PadhamNumber`).

| Column | Role |
|--------|------|
| `Pasuram` | Full verse (same on every padham row of that verse) |
| `PasuramWordsSplit` | Recitation-split verse (UAT; `*` splits; leading `●` = recite twice) |
| `Padham` | Tamil split token |
| `Word` | `padham, Transliteration` |
| `Meaning` | Padha artham for that token |
| `PadhamNumber` | Order of the split (1, 2, 3…) |
| `SimilarWords` | Search hooks (not the recitation split itself) |

UI PadhaArtham column lists `Word` + `Meaning` per row (`பதவுரை Show / Hide`). Path G prabandhams (no padham) use one row, empty `Word`/`Padham`, `Meaning` as simple explanation.

## How to work in a new session

1. Read this skill first. Session handoff: [docs/SESSION_RESUME.md](../../../docs/SESSION_RESUME.md) (Pasuram-Split section at the top).
2. For recitation splits: UAT table + `test1.php` unless the user names POC/prod.
3. **Do not resume Acharya PDF loads.** Next splits come from the user’s scanned book uploads, one batch at a time.
4. Keep existing UAT `PasuramWordsSplit` (Pallandu 1–12; பெரியாழ்வார் திருமொழி 13–222) until the user asks to replace a range.
5. For ingest/load/Kannadi/counts, follow [prabandham-ingest](../prabandham-ingest/SKILL.md) and [docs/PASURAM_INGESTION_PIPELINE.md](../../../docs/PASURAM_INGESTION_PIPELINE.md).

## Status

**Paused.** Acharya PDF iteration stopped — book splits differ. UAT still has திருப்பல்லாண்டு **1–12** and பெரியாழ்வார் திருமொழி **13–222**; `Pasuram` unchanged. Wait for scanned book pages. Do not copy split → `Pasuram` until asked.
