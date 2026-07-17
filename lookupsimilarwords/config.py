from __future__ import annotations

import configparser
from pathlib import Path
from typing import Dict


def load_db_config(config_path: Path) -> Dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    if "db" not in parser:
        raise ValueError("Missing [db] section in config file")

    db_config = {
        "host": parser.get("db", "host", fallback="localhost"),
        "port": parser.getint("db", "port", fallback=3306),
        "user": parser.get("db", "user", fallback=""),
        "password": parser.get("db", "password", fallback=""),
        "database": parser.get("db", "database", fallback=""),
        "table": parser.get("db", "table", fallback=""),
        "use_ssl": parser.getboolean("db", "use_ssl", fallback=False),
    }

    return db_config
