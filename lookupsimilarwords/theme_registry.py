#!/usr/bin/env python3
"""Load theme definitions from theme_registry.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

LOOKUP_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY_PATH = LOOKUP_DIR / "theme_registry.json"
DEFAULT_DETECTORS_DIR = LOOKUP_DIR / "detectors"


def load_theme_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    registry_path = path or DEFAULT_REGISTRY_PATH
    with registry_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def list_theme_ids(registry: Optional[Dict[str, Any]] = None) -> List[str]:
    data = registry or load_theme_registry()
    themes = data.get("themes", {})
    return sorted(themes.keys(), key=lambda tid: themes[tid].get("rule", 999))


def get_theme(theme_id: str, registry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = registry or load_theme_registry()
    themes = data.get("themes", {})
    if theme_id not in themes:
        raise KeyError(f"Unknown theme id: {theme_id!r}. Available: {', '.join(sorted(themes))}")
    return themes[theme_id]


def detector_path_for_theme(
    theme_id: str,
    detectors_dir: Optional[Path] = None,
) -> Path:
    base = detectors_dir or DEFAULT_DETECTORS_DIR
    return base / f"{theme_id}_detector.json"


def resolve_theme_ids(theme_arg: Optional[str], registry: Optional[Dict[str, Any]] = None) -> List[str]:
    if not theme_arg or theme_arg.strip().lower() == "all":
        return list_theme_ids(registry)
    return [part.strip() for part in theme_arg.split(",") if part.strip()]
