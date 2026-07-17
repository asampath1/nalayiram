#!/usr/bin/env python3
"""Load JSON-produced POC records into MySQL using tested insertion logic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import mysql.connector
from mysql.connector.connection import MySQLConnection


def _connect_db(config) -> MySQLConnection:
    kwargs = {
        "host": config.host,
        "port": config.port,
        "user": config.user,
        "password": config.password,
        "database": config.database,
    }
    if config.use_ssl:
        kwargs["ssl_disabled"] = False
    return mysql.connector.connect(**kwargs)


def _get_next_sno(cursor, table: str) -> int:
    cursor.execute(f"SELECT MAX(Sno) FROM {table}")
    row = cursor.fetchone()
    max_sno = row[0] if row and row[0] is not None else 0
    return max_sno + 1


def _load_records(json_path: Path) -> List[Dict]:
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict):
        # support legacy dict-of-arrays format
        records: List[Dict] = []
        for values in data.values():
            if isinstance(values, list):
                records.extend(values)
        return records

    if isinstance(data, list):
        return data

    raise ValueError("Unsupported JSON structure: expected list or dict")


def load_json_to_db(json_path: Path, config, dry_run: bool = False) -> int:
    records = _load_records(json_path)
    conn = _connect_db(config)
    cursor = conn.cursor()
    next_sno = _get_next_sno(cursor, config.table)
    records_inserted = 0

    insert_query = f"""
    INSERT INTO {config.table}
    (Sno, Prabandham, PasuramNumber, Pasuram, PattuNumber, Word, SimilarWords, Padham, Meaning, Alzwar, PadhamNumber, Title, NithyaanusandhamIndex)
    VALUES (%(Sno)s, %(Prabandham)s, %(PasuramNumber)s, %(Pasuram)s, %(PattuNumber)s, %(Word)s, %(SimilarWords)s, %(Padham)s, %(Meaning)s, %(Alzwar)s, %(PadhamNumber)s, %(Title)s, %(NithyaanusandhamIndex)s)
    """

    for record in records:
        record.setdefault("NithyaanusandhamIndex", None)
        record["Sno"] = next_sno
        next_sno += 1

        if dry_run:
            print(f"DRY RUN: would insert Sno={record['Sno']} PasuramNumber={record.get('PasuramNumber')} PadhamNumber={record.get('PadhamNumber')}")
            records_inserted += 1
            continue

        try:
            cursor.execute(insert_query, record)
            conn.commit()
            records_inserted += 1
            print(f"Inserted Sno={record['Sno']} PasuramNumber={record.get('PasuramNumber')} PadhamNumber={record.get('PadhamNumber')}")
        except mysql.connector.Error as err:
            print(f"Error inserting record Sno={record['Sno']}: {err}")
            continue

    cursor.close()
    conn.close()
    return records_inserted
