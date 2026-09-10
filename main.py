#!/usr/bin/env python3
"""yt-dlp CustomTkinter GUI — entry point."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path when run as script
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _crash_log_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    folder = Path(base) / "yt-dlp-gui"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "crash.log"


def _write_crash(exc: BaseException) -> Path:
    path = _crash_log_path()
    with path.open("w", encoding="utf-8") as f:
        f.write("yt-dlp-gui crash\n")
        f.write(f"frozen={getattr(sys, 'frozen', False)}\n")
        f.write(f"executable={sys.executable}\n\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
    return path


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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — last-resort crash log for windowed exe
        try:
            log_path = _write_crash(exc)
            # Best-effort message box when frozen (no console)
            if getattr(sys, "frozen", False) and sys.platform == "win32":
                try:
                    import ctypes

                    ctypes.windll.user32.MessageBoxW(
                        0,
                        f"yt-dlp GUI crashed.\n\nDetails written to:\n{log_path}",
                        "yt-dlp GUI",
                        0x10,
                    )
                except Exception:
                    pass
            else:
                print(f"Crash logged to: {log_path}", file=sys.stderr)
                traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        except Exception:
            pass
        raise SystemExit(1)
