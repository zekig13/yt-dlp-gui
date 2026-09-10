"""Persist GUI settings to %APPDATA%/yt-dlp-gui/settings.json (Windows)."""
from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_NAME = "yt-dlp-gui"

DEFAULTS: dict[str, Any] = {
    "ytdlp_path": r"C:\yt-dlp\yt-dlp.exe",
    "cookies_path": r"C:\yt-dlp\cookies.txt",
    "output_dir": str(Path.home() / "Downloads"),
    "output_template": "%(title)s [%(id)s].%(ext)s",
    "format_shortcut": "best",
    "urls": "",
    "window_geometry": "1100x780",
    "appearance_mode": "System",
    "color_theme": "blue",
    "option_values": {},  # option_id -> value (bool / str / list)
}


def settings_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return settings_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    data = deepcopy(DEFAULTS)
    path = settings_path()
    if path.is_file():
        try:
            with path.open(encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for k, v in saved.items():
                    if k in DEFAULTS or k == "option_values":
                        data[k] = v
        except (OSError, json.JSONDecodeError):
            pass
    if not isinstance(data.get("option_values"), dict):
        data["option_values"] = {}
    return data


def save_settings(data: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    to_save = {**DEFAULTS, **data}
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
