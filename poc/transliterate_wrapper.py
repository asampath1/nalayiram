#!/usr/bin/env python3
"""Transliteration wrapper with persistent JSON cache and in-memory LRU.

Usage:
  - Import `Transliterator` and call `transliterator.transliterate(text)` or
    `transliterator.batch_translate(list_of_texts)`.

Notes:
  - By default, this wrapper will not call any external API unless a
    `transliteration_cmd` is provided in the `Transliterator` constructor.
  - The cache is stored at `poc/cache/transliteration_cache.json` by default.
"""
from __future__ import annotations

import json
import os
import tempfile
import shutil
import unicodedata
import time
import logging
import subprocess
from typing import Dict, List, Optional, Tuple

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _atomic_write(path: str, data: str) -> None:
    dirpath = os.path.dirname(path)
    _ensure_dir(dirpath)
    fd, tmp = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


class TransliterationCache:
    """Persistent JSON-backed cache with simple TTL support.

    Cache structure (JSON):
      { "normalized_key": {"transliteration": "...", "source": "api|cache|stub", "ts": 1670000000} }
    """

    def __init__(self, path: str = "poc/cache/transliteration_cache.json", ttl_seconds: Optional[int] = None):
        self.path = path
        self.ttl = ttl_seconds
        self._mem_cache: Dict[str, Dict] = {}
        self._load()

    @staticmethod
    def normalize_key(text: str) -> str:
        if text is None:
            return ""
        s = unicodedata.normalize("NFC", text).strip()
        return s

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._disk_cache: Dict[str, Dict] = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._disk_cache = json.load(f)
        except Exception:
            LOGGER.exception("Failed to load transliteration cache; starting empty")
            self._disk_cache = {}

    def _save(self) -> None:
        try:
            _atomic_write(self.path, json.dumps(self._disk_cache, ensure_ascii=False, indent=2))
        except Exception:
            LOGGER.exception("Failed to save transliteration cache")

    def get(self, text: str) -> Optional[Tuple[str, str]]:
        key = self.normalize_key(text)
        # check in-memory
        entry = self._mem_cache.get(key)
        if entry:
            if not self._expired(entry):
                return entry["transliteration"], entry.get("source", "mem")
            else:
                self._mem_cache.pop(key, None)

        # check disk
        entry = self._disk_cache.get(key)
        if entry and not self._expired(entry):
            # populate mem cache for faster subsequent access
            self._mem_cache[key] = entry
            return entry["transliteration"], entry.get("source", "disk")

        return None

    def set(self, text: str, transliteration: str, source: str = "api") -> None:
        key = self.normalize_key(text)
        entry = {"transliteration": transliteration, "source": source, "ts": int(time.time())}
        self._disk_cache[key] = entry
        self._mem_cache[key] = entry
        self._save()

    def _expired(self, entry: Dict) -> bool:
        if self.ttl is None:
            return False
        ts = entry.get("ts", 0)
        return (time.time() - ts) > self.ttl

    def flush(self) -> None:
        self._disk_cache = {}
        self._mem_cache = {}
        self._save()


class Transliterator:
    """Transliterator that consults cache and falls back to an external command.

    The external command (if provided) should accept newline-separated UTF-8
    inputs on stdin and return JSON mapping of input->transliteration on stdout,
    or output newline-separated transliterations in the same order. If no
    command is provided the wrapper falls back to returning the original
    Tamil string (useful for dry runs).
    """

    def __init__(self, cache: Optional[TransliterationCache] = None, transliteration_cmd: Optional[List[str]] = None, batch_size: int = 10):
        self.cache = cache or TransliterationCache()
        self.cmd = transliteration_cmd
        self.batch_size = batch_size

    def transliterate(self, text: str) -> str:
        res = self.get_from_cache(text)
        if res is not None:
            return res
        # Not in cache — call batch handler with single item
        out = self.batch_translate([text])
        return out.get(text, text)

    def get_from_cache(self, text: str) -> Optional[str]:
        v = self.cache.get(text)
        if v:
            translit, src = v
            LOGGER.debug("Cache hit for text (src=%s)", src)
            return translit
        return None

    def batch_translate(self, texts: List[str]) -> Dict[str, str]:
        # Normalize keys and check cache
        result: Dict[str, str] = {}
        missing: List[str] = []
        seen = set()
        for t in texts:
            if t in seen:
                continue
            seen.add(t)
            v = self.cache.get(t)
            if v:
                result[t] = v[0]
            else:
                missing.append(t)

        if not missing:
            return result

        # Process in batches
        for i in range(0, len(missing), self.batch_size):
            batch = missing[i : i + self.batch_size]
            try:
                translations = self._call_external(batch)
            except Exception:
                LOGGER.exception("External transliteration failed; falling back to identity")
                translations = {t: t for t in batch}

            # store
            for t in batch:
                translit = translations.get(t, t)
                self.cache.set(t, translit, source=("api" if self.cmd else "stub"))
                result[t] = translit

        return result

    def _call_external(self, texts: List[str]) -> Dict[str, str]:
        if not self.cmd:
            # Dry-run fallback
            return {t: t for t in texts}

        # Try to call command: send newline-separated inputs on stdin
        proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        input_payload = "\n".join(texts)
        out, err = proc.communicate(input_payload)
        if proc.returncode != 0:
            LOGGER.error("Transliteration command failed: %s", err)
            raise RuntimeError("transliteration command failed")

        # First try parse as JSON mapping
        try:
            parsed = json.loads(out)
            # parsed should be mapping or list
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list) and len(parsed) == len(texts):
                return {t: parsed[idx] for idx, t in enumerate(texts)}
        except Exception:
            # Not JSON, treat as newline-separated outputs
            lines = out.splitlines()
            if len(lines) == len(texts):
                return {t: lines[idx] for idx, t in enumerate(texts)}

        # If we reach here, return identity mapping
        LOGGER.warning("Unexpected transliteration output; returning input as transliteration")
        return {t: t for t in texts}


if __name__ == "__main__":
    # simple CLI for quick checks
    import argparse

    p = argparse.ArgumentParser(description="Transliteration wrapper CLI (test)")
    p.add_argument("text", nargs="*", help="Tamil padham text(s) to transliterate")
    p.add_argument("--cache-ttl", type=int, default=None, help="Cache TTL in seconds")
    p.add_argument("--cmd", nargs=argparse.REMAINDER, help="External transliteration command to call")
    args = p.parse_args()

    cache = TransliterationCache(ttl_seconds=args.cache_ttl)
    transliterator = Transliterator(cache=cache, transliteration_cmd=args.cmd)
    inputs = args.text or []
    res = transliterator.batch_translate(inputs)
    print(json.dumps(res, ensure_ascii=False, indent=2))
