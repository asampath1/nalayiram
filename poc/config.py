#!/usr/bin/env python3
"""Configuration loader for the POC pipeline."""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ScraperConfig:
    base_url: str
    start: int
    end: int
    prabandham: str
    title: str
    alzwar: Optional[str]
    pattu_number: Optional[int]
    pattu_number_start: Optional[int]


@dataclass
class CacheConfig:
    path: str
    ttl_seconds: Optional[int]


@dataclass
class TransliterationConfig:
    command: Optional[str]
    use_gpt_adapter: bool
    batch_size: int


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    table: str
    use_ssl: bool


@dataclass
class POCConfig:
    scraper: ScraperConfig
    cache: CacheConfig
    transliteration: TransliterationConfig
    database: DatabaseConfig


def _read_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config(path: Optional[str] = None) -> POCConfig:
    config_path = Path(path or "poc/config.ini")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    scraper = ScraperConfig(
        base_url=parser.get("scraper", "base_url", fallback="https://www.dravidaveda.org"),
        start=_read_int(parser.get("scraper", "start", fallback="0"), 0),
        end=_read_int(parser.get("scraper", "end", fallback="0"), 0),
        prabandham=parser.get("scraper", "prabandham", fallback=""),
        title=parser.get("scraper", "title", fallback=""),
        alzwar=parser.get("scraper", "alzwar", fallback="") or None,
        pattu_number=_read_int(parser.get("scraper", "pattu_number", fallback="0"), 0) or None,
        pattu_number_start=_read_int(parser.get("scraper", "pattu_number_start", fallback="0"), 0) or None,
    )

    cache = CacheConfig(
        path=parser.get("cache", "path", fallback="poc/cache/transliteration_cache.json"),
        ttl_seconds=_read_int(parser.get("cache", "ttl_seconds", fallback="0"), 0) or None,
    )

    transliteration = TransliterationConfig(
        command=parser.get("transliteration", "transliteration_cmd", fallback="") or None,
        use_gpt_adapter=parser.getboolean("transliteration", "use_gpt_adapter", fallback=False),
        batch_size=_read_int(parser.get("poc", "batch_size", fallback="10"), 10),
    )

    database = DatabaseConfig(
        host=parser.get("db", "host", fallback="localhost"),
        port=_read_int(parser.get("db", "port", fallback="3306"), 3306),
        user=parser.get("db", "user", fallback=""),
        password=parser.get("db", "password", fallback=""),
        database=parser.get("db", "database", fallback=""),
        table=parser.get("db", "table", fallback="PasuramsArthamTablePOC"),
        use_ssl=parser.getboolean("db", "use_ssl", fallback=False),
    )

    return POCConfig(scraper=scraper, cache=cache, transliteration=transliteration, database=database)
