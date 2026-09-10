"""Run yt-dlp as a subprocess with streamed output and cancel support."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import TextIO


OnLine = Callable[[str], None]
OnDone = Callable[[int | None], None]


def _win_hide_console_flags(extra: int = 0) -> int:
    if sys.platform != "win32":
        return 0
    # Avoid flashing black console windows when a GUI app spawns CLI tools.
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)) | extra


def _win_startupinfo():
    if sys.platform != "win32":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info


class DownloadRunner:
    """Manage a single yt-dlp process."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def start(
        self,
        argv: list[str],
        *,
        on_line: OnLine | None = None,
        on_done: OnDone | None = None,
        cwd: str | None = None,
        path_prepend: str | list[str] | None = None,
    ) -> None:
        if self.is_running:
            raise RuntimeError("Bir indirme zaten çalışıyor")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = _win_hide_console_flags(
                int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            )

        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        if path_prepend:
            parts = path_prepend if isinstance(path_prepend, list) else [path_prepend]
            prefix = os.pathsep.join(p for p in parts if p)
            if prefix:
                env["PATH"] = prefix + os.pathsep + env.get("PATH", "")

        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=cwd or None,
            env=env,
            creationflags=creationflags,
            startupinfo=_win_startupinfo(),
        )
        with self._lock:
            self._proc = proc

        def _reader() -> None:
            assert proc.stdout is not None
            stream: TextIO = proc.stdout
            try:
                for line in stream:
                    if on_line:
                        on_line(line.rstrip("\r\n"))
            finally:
                try:
                    stream.close()
                except OSError:
                    pass
            code = proc.wait()
            with self._lock:
                if self._proc is proc:
                    self._proc = None
            if on_done:
                on_done(code)

        self._thread = threading.Thread(target=_reader, name="ytdlp-runner", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        pid = proc.pid
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=_win_hide_console_flags(),
                    startupinfo=_win_startupinfo(),
                )
            else:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError, OSError):
                    proc.terminate()
        except OSError:
            try:
                proc.kill()
            except OSError:
                pass
