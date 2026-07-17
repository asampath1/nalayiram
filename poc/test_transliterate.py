#!/usr/bin/env python3
"""Small test runner for the transliteration wrapper.

This script demonstrates usage and verifies the cache write/read behavior.
"""
from poc.transliterate_wrapper import TransliterationCache, Transliterator


def main():
    cache = TransliterationCache(path="poc/cache/transliteration_cache.json")
    transliterator = Transliterator(cache=cache, transliteration_cmd=None)

    samples = [
        "பலண்ணு",
        "மல்லண்டு",
        "பலண்ணு",  # duplicate to exercise cache
    ]

    out = transliterator.batch_translate(samples)
    for k, v in out.items():
        print(f"{k} -> {v}")


if __name__ == '__main__':
    main()
