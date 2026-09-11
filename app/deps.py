"""Auto-provision yt-dlp.exe, ffmpeg, and deno into %LOCALAPPDATA%\\yt-dlp-gui\\bin."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "yt-dlp-gui"

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

# Essentials builds (~80MB zip) — prefer gyan, fall back to BtbN
FFMPEG_ZIP_URLS = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip",
)

# Official Deno Windows x64 zip (contains deno.exe)
DENO_ZIP_URL = (
    "https://github.com/denoland/deno/releases/latest/download/"
    "deno-x86_64-pc-windows-msvc.zip"
)

ProgressCb = Callable[[str, float | None], None]


@dataclass(frozen=True)
class ToolPaths:
    bin_dir: Path
    ytdlp: Path
    ffmpeg: Path
    ffprobe: Path
    deno: Path

    def as_env_path_prefix(self) -> str:
        return str(self.bin_dir)


def managed_bin_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(
            Path.home() / "AppData" / "Local"
        )
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_NAME / "bin"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_ytdlp_path() -> str:
    return str(managed_bin_dir() / ("yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"))


def tool_paths() -> ToolPaths:
    bin_dir = managed_bin_dir()
    exe = ".exe" if sys.platform == "win32" else ""
    return ToolPaths(
        bin_dir=bin_dir,
        ytdlp=bin_dir / f"yt-dlp{exe}",
        ffmpeg=bin_dir / f"ffmpeg{exe}",
        ffprobe=bin_dir / f"ffprobe{exe}",
        deno=bin_dir / f"deno{exe}",
    )


def _report(progress: ProgressCb | None, message: str, fraction: float | None = None) -> None:
    if progress:
        progress(message, fraction)


def _download_file(
    url: str,
    dest: Path,
    *,
    progress: ProgressCb | None = None,
    label: str = "İndiriliyor",
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "yt-dlp-gui/1.3 (dependency bootstrap)",
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            total = resp.headers.get("Content-Length")
            total_n = int(total) if total and total.isdigit() else None
            done = 0
            chunk = 256 * 1024
            with tmp.open("wb") as out:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    out.write(data)
                    done += len(data)
                    if total_n:
                        frac = min(done / total_n, 1.0)
                        mb = done / (1024 * 1024)
                        total_mb = total_n / (1024 * 1024)
                        _report(
                            progress,
                            f"{label}: {mb:.1f}/{total_mb:.1f} MB",
                            frac,
                        )
                    else:
                        mb = done / (1024 * 1024)
                        _report(progress, f"{label}: {mb:.1f} MB…", None)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"İndirme başarısız ({exc.code}): {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ağ hatası: {exc.reason}") from exc

    tmp.replace(dest)


def _win_hide_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return {
        "startupinfo": info,
        "creationflags": int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)),
    }


def _run_version(argv: list[str]) -> str:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            **_win_hide_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Sürüm kontrolü başarısız: {argv[0]} — {exc}") from exc
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 and not out.strip():
        raise RuntimeError(f"Sürüm kontrolü çıkış kodu {proc.returncode}: {argv[0]}")
    return out.strip().splitlines()[0] if out.strip() else ""


def _ytdlp_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        _run_version([str(path), "--version"])
        return True
    except RuntimeError:
        return False


def _ffmpeg_ok(ffmpeg: Path, ffprobe: Path) -> bool:
    if not ffmpeg.is_file() or not ffprobe.is_file():
        return False
    try:
        _run_version([str(ffmpeg), "-version"])
        _run_version([str(ffprobe), "-version"])
        return True
    except RuntimeError:
        return False


def _deno_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        _run_version([str(path), "--version"])
        return True
    except RuntimeError:
        return False


def _ensure_ytdlp(paths: ToolPaths, progress: ProgressCb | None) -> None:
    if _ytdlp_ok(paths.ytdlp):
        ver = _run_version([str(paths.ytdlp), "--version"])
        _report(progress, f"yt-dlp hazır ({ver})", 1.0)
        return
    _report(progress, "yt-dlp indiriliyor…", 0.0)
    _download_file(YTDLP_URL, paths.ytdlp, progress=progress, label="yt-dlp")
    if not _ytdlp_ok(paths.ytdlp):
        raise RuntimeError(
            "yt-dlp indirildi ancak çalıştırılamadı. Antivirüs engelliyor olabilir."
        )
    ver = _run_version([str(paths.ytdlp), "--version"])
    _report(progress, f"yt-dlp hazır ({ver})", 1.0)


def _extract_ffmpeg_binaries(zip_path: Path, dest_dir: Path, progress: ProgressCb | None) -> None:
    needed = {"ffmpeg.exe", "ffprobe.exe"}
    optional = {"ffplay.exe"}
    found: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name.lower()
            if name in needed or name in optional:
                # Prefer bin/ folder entries over duplicates
                prev = found.get(name)
                if prev is None or "/bin/" in info.filename.replace("\\", "/").lower():
                    found[name] = info
        missing = needed - set(found)
        if missing:
            raise RuntimeError(
                f"Zip içinde beklenen dosyalar yok: {', '.join(sorted(missing))}"
            )
        _report(progress, "ffmpeg çıkarılıyor…", 0.85)
        for name, info in found.items():
            target = dest_dir / Path(info.filename).name
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)


def _ensure_ffmpeg(paths: ToolPaths, progress: ProgressCb | None) -> None:
    if _ffmpeg_ok(paths.ffmpeg, paths.ffprobe):
        ver = _run_version([str(paths.ffmpeg), "-version"])
        _report(progress, f"ffmpeg hazır ({ver})", 1.0)
        return

    last_err: Exception | None = None
    with tempfile.TemporaryDirectory(prefix="ytdlp-gui-ffmpeg-") as tmp:
        zip_path = Path(tmp) / "ffmpeg.zip"
        for i, url in enumerate(FFMPEG_ZIP_URLS):
            try:
                _report(
                    progress,
                    f"ffmpeg indiriliyor (kaynak {i + 1}/{len(FFMPEG_ZIP_URLS)})…",
                    0.0,
                )
                _download_file(url, zip_path, progress=progress, label="ffmpeg")
                _extract_ffmpeg_binaries(zip_path, paths.bin_dir, progress)
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001 — try next mirror
                last_err = exc
                _report(progress, f"Kaynak başarısız, deneniyor… ({exc})", None)
        if last_err is not None:
            raise RuntimeError(
                f"ffmpeg indirilemedi. Son hata: {last_err}"
            ) from last_err

    if not _ffmpeg_ok(paths.ffmpeg, paths.ffprobe):
        raise RuntimeError(
            "ffmpeg çıkarıldı ancak çalıştırılamadı. Antivirüs engelliyor olabilir."
        )
    ver = _run_version([str(paths.ffmpeg), "-version"])
    _report(progress, f"ffmpeg hazır ({ver})", 1.0)


def _extract_deno_binary(zip_path: Path, dest_dir: Path, progress: ProgressCb | None) -> None:
    target_name = "deno.exe" if sys.platform == "win32" else "deno"
    with zipfile.ZipFile(zip_path, "r") as zf:
        match: zipfile.ZipInfo | None = None
        for info in zf.infolist():
            if info.is_dir():
                continue
            if Path(info.filename).name.lower() == target_name.lower():
                match = info
                break
        if match is None:
            raise RuntimeError(f"Zip içinde {target_name} yok")
        _report(progress, "Deno çıkarılıyor…", 0.9)
        target = dest_dir / target_name
        with zf.open(match) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out)


def _ensure_deno(paths: ToolPaths, progress: ProgressCb | None) -> None:
    if _deno_ok(paths.deno):
        ver = _run_version([str(paths.deno), "--version"])
        _report(progress, f"Deno hazır ({ver})", 1.0)
        return

    _report(progress, "Deno indiriliyor…", 0.0)
    with tempfile.TemporaryDirectory(prefix="ytdlp-gui-deno-") as tmp:
        zip_path = Path(tmp) / "deno.zip"
        _download_file(DENO_ZIP_URL, zip_path, progress=progress, label="Deno")
        _extract_deno_binary(zip_path, paths.bin_dir, progress)

    if not _deno_ok(paths.deno):
        raise RuntimeError(
            "Deno çıkarıldı ancak çalıştırılamadı. Antivirüs engelliyor olabilir."
        )
    ver = _run_version([str(paths.deno), "--version"])
    _report(progress, f"Deno hazır ({ver})", 1.0)


def ensure_dependencies(
    *,
    progress: ProgressCb | None = None,
    force_ytdlp: bool = False,
    force_ffmpeg: bool = False,
    force_deno: bool = False,
) -> ToolPaths:
    """Download yt-dlp + ffmpeg + deno into managed bin dir if missing/broken.

    Returns absolute tool paths. Raises RuntimeError with a Turkish message on failure.
    """
    paths = tool_paths()
    _report(progress, "Araçlar hazırlanıyor…", 0.0)

    if force_ytdlp and paths.ytdlp.exists():
        try:
            paths.ytdlp.unlink()
        except OSError:
            pass
    if force_ffmpeg:
        for p in (paths.ffmpeg, paths.ffprobe, paths.bin_dir / "ffplay.exe"):
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
    if force_deno and paths.deno.exists():
        try:
            paths.deno.unlink()
        except OSError:
            pass

    try:
        _ensure_ytdlp(paths, progress)
        _ensure_ffmpeg(paths, progress)
        _ensure_deno(paths, progress)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Araç kurulumu başarısız: {exc}") from exc

    _report(progress, "Araçlar hazır", 1.0)
    return paths


def verify_tools(paths: ToolPaths | None = None) -> tuple[bool, str]:
    """Return (ok, summary_message)."""
    p = paths or tool_paths()
    parts: list[str] = []
    ok = True
    if _ytdlp_ok(p.ytdlp):
        parts.append(f"yt-dlp: {_run_version([str(p.ytdlp), '--version'])}")
    else:
        ok = False
        parts.append("yt-dlp: eksik")
    if _ffmpeg_ok(p.ffmpeg, p.ffprobe):
        parts.append(f"ffmpeg: {_run_version([str(p.ffmpeg), '-version'])}")
    else:
        ok = False
        parts.append("ffmpeg: eksik")
    if _deno_ok(p.deno):
        parts.append(f"deno: {_run_version([str(p.deno), '--version'])}")
    else:
        ok = False
        parts.append("deno: eksik")
    return ok, " | ".join(parts)
