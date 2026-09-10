#!/usr/bin/env python3
"""yt-dlp CustomTkinter GUI — entry point."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when run as script
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        print(
            "customtkinter eksik. Kurulum:\n  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    from app.ui.main_window import run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
