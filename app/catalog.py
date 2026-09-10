"""Load and query the yt-dlp options catalog."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parent / "options_catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        raise FileNotFoundError(
            f"Catalog missing: {_CATALOG_PATH}. Run scripts/generate_catalog.py"
        )
    with _CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def iter_options(catalog: dict[str, Any] | None = None):
    cat = catalog or load_catalog()
    for section in cat.get("sections", []):
        for opt in section.get("options", []):
            yield section, opt


def filter_catalog(query: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a shallow-filtered catalog copy matching query (flags/help/title)."""
    cat = catalog or load_catalog()
    q = (query or "").strip().lower()
    if not q:
        return cat
    sections = []
    for section in cat.get("sections", []):
        opts = []
        for opt in section.get("options", []):
            blob = " ".join(
                [
                    section.get("title", ""),
                    section.get("title_tr", ""),
                    " ".join(opt.get("flags", [])),
                    opt.get("primary", ""),
                    opt.get("metavar") or "",
                    opt.get("help") or "",
                    opt.get("preset_value") or "",
                    opt.get("id", ""),
                ]
            ).lower()
            if q in blob:
                opts.append(opt)
        if opts:
            sec = dict(section)
            sec["options"] = opts
            sections.append(sec)
    return {
        "source": cat.get("source"),
        "option_count": sum(len(s["options"]) for s in sections),
        "section_count": len(sections),
        "sections": sections,
        "filtered": True,
        "query": query,
    }
