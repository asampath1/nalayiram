import os
import json
import re
import unicodedata
import asyncio
import pandas as pd
from openai import AsyncOpenAI

# ---------------- CONFIG ----------------
MODEL_NAME = "gpt-4o-mini"
LINES_PER_CHUNK = 20
MAX_CONCURRENT = 5
MAX_RETRIES = 3

DICT_PATH = "/Users/anand/tensorflow-test/4K Pasuram/transliterate_cache.json"
INPUT_XLSX = "/Users/anand/tensorflow-test/4K Pasuram/transliterate.xlsx"
OUTPUT_XLSX = "/Users/anand/tensorflow-test/4K Pasuram/transliterate_output1.xlsx"

client = AsyncOpenAI()  # uses OPENAI_API_KEY

# ---------------- PROMPT ----------------
SYSTEM_PROMPT = """You are a Tamil to English transliteration engine.

Rules:
- Output ONLY transliterated text
- No explanations
- No special characters, punctuation, or emojis
- Use only ASCII letters and spaces
- Each input line must produce exactly one output line
- Maintain same number of lines
- No empty lines
- First letter uppercase per word
- Output newline separated
"""

# ---------------- DICTIONARY ----------------
def load_dict():
    if os.path.exists(DICT_PATH):
        try:
            with open(DICT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception as e:
            print(f"Warning: Could not load cache dictionary: {e}. Using empty cache.")
            return {}
    return {}

def save_dict(d):
    with open(DICT_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

cache_dict = load_dict()

# ---------------- SANITIZE OUTPUT ----------------

def sanitize_line(line):
    # Normalize accents and remove any non-ASCII characters, leaving only letters, numbers, and spaces.
    line = line.strip()
    line = unicodedata.normalize("NFKD", line)
    line = line.encode("ascii", "ignore").decode("ascii")
    line = re.sub(r"[^A-Za-z0-9 ]+", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.title()

# ---------------- GPT CALL ----------------
async def call_gpt(lines):
    text = "\n".join(lines)

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
    )

    output = response.choices[0].message.content.strip()
    result = [sanitize_line(l) for l in output.split("\n") if l.strip()]
    return result

# ---------------- PROCESS BATCH ----------------
async def process_batch(batch, semaphore):
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                results = await call_gpt(batch)

                if len(results) != len(batch):
                    raise ValueError("Line mismatch")

                return results

            except Exception as e:
                print(f"Retry {attempt+1} failed: {e}")
                await asyncio.sleep(1)

        return [None] * len(batch)

# ---------------- MAIN ----------------
async def main():
    df = pd.read_excel(INPUT_XLSX)

    # Assume Column A = Padam
    input_lines = df.iloc[:, 0].astype(str).tolist()

    results = [None] * len(input_lines)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = []
    batch_indices = []

    # ---- Prepare batches (with cache check) ----
    i = 0
    while i < len(input_lines):
        batch = input_lines[i:i+LINES_PER_CHUNK]

        # Check cache
        uncached = []
        uncached_indices = []

        for j, line in enumerate(batch):
            if line in cache_dict:
                sanitized = sanitize_line(cache_dict[line])
                results[i+j] = sanitized
                cache_dict[line] = sanitized
            else:
                uncached.append(line)
                uncached_indices.append(i+j)

        if uncached:
            tasks.append(process_batch(uncached, semaphore))
            batch_indices.append(uncached_indices)

        i += LINES_PER_CHUNK

    print(f"Processing {len(tasks)} async batches...")

    # ---- Run async ----
    batch_outputs = await asyncio.gather(*tasks)

    # ---- Fill results ----
    for indices, outputs in zip(batch_indices, batch_outputs):
        for idx, out in zip(indices, outputs):
            results[idx] = out
            cache_dict[input_lines[idx]] = out

    # Save dictionary
    save_dict(cache_dict)

    # Write output
    df["Word"] = results
    df.to_excel(OUTPUT_XLSX, index=False)

    print("✅ Done! Saved to", OUTPUT_XLSX)

# ---------------- RUN ----------------
if __name__ == "__main__":
    asyncio.run(main())