"""Build yt-dlp argv from GUI state."""
from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

# Format shortcut -> extra argv fragments (applied when not overridden by options)
FORMAT_SHORTCUTS: dict[str, list[str]] = {
    "best": ["-f", "bv*+ba/b"],
    "bestvideo+bestaudio": ["-f", "bestvideo+bestaudio/best"],
    "worst": ["-f", "worst"],
    "mp4": ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"],
    "webm": ["-f", "bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/bv*+ba/b"],
    "audio-best": ["-f", "ba/b", "-x"],
    "mp3": ["-f", "ba/b", "-x", "--audio-format", "mp3"],
    "m4a": ["-f", "ba/b", "-x", "--audio-format", "m4a"],
    "custom": [],  # use -f from options panel if set
}


def _quote_preview(arg: str) -> str:
    if not arg:
        return '""'
    if any(c in arg for c in ' \t\n\r"\'&|<>^'):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def build_command(
    *,
    ytdlp_path: str,
    urls: list[str],
    output_dir: str,
    output_template: str,
    format_shortcut: str,
    cookies_path: str,
    option_values: dict[str, Any],
    catalog: dict[str, Any],
    deno_path: str | None = None,
    cookies_source: str | None = None,
) -> list[str]:
    """Return argv list (executable first)."""
    cmd: list[str] = [ytdlp_path or "yt-dlp"]

    # Main panel paths / template
    if output_dir:
        cmd.extend(["-P", "home:" + str(Path(output_dir))])
    if output_template:
        cmd.extend(["-o", output_template])

    # Cookies: browser XOR file (never both — yt-dlp rejects the combo)
    source = (cookies_source or "").strip().lower()
    if not source:
        # Back-compat: infer from path if caller omitted cookies_source
        source = "file" if (cookies_path or "").strip() else "none"
    browser_names = {"chrome", "edge", "firefox"}
    if source in browser_names:
        cmd.extend(["--cookies-from-browser", source])
    elif source == "file":
        cookies = (cookies_path or "").strip()
        if cookies and Path(cookies).is_file():
            cmd.extend(["--cookies", cookies])
        elif cookies:
            # Still pass if user set a path (file may appear later)
            cmd.extend(["--cookies", cookies])
    # source == "none" (or unknown): omit both

    # Explicit Deno path for YouTube JS challenges (also keep managed bin on PATH)
    deno = (deno_path or "").strip()
    if deno and Path(deno).is_file():
        cmd.extend(["--js-runtimes", f"deno:{deno}"])

    # Track which primary flags are already supplied by option_values
    supplied: set[str] = set()
    id_to_opt: dict[str, dict] = {}
    for section in catalog.get("sections", []):
        for opt in section.get("options", []):
            id_to_opt[opt["id"]] = opt

    # Format shortcut unless -f/--format already in option_values
    format_from_opts = False
    for oid, val in (option_values or {}).items():
        opt = id_to_opt.get(oid)
        if not opt:
            continue
        if opt.get("type") == "bool" and not val:
            continue
        if opt.get("type") in ("value", "choice") and (val is None or val == ""):
            continue
        if opt.get("type") == "preset" and not val:
            continue
        for f in opt.get("flags", []):
            supplied.add(f)
        if any(f in ("-f", "--format") for f in opt.get("flags", [])):
            format_from_opts = True

    if not format_from_opts:
        frag = FORMAT_SHORTCUTS.get(format_shortcut or "best", FORMAT_SHORTCUTS["best"])
        cmd.extend(frag)

    # Catalog options (skip presets handled specially; skip main_panel duplicates
    # for -o/-P/--cookies which we already set — unless user explicitly set them
    # and we want catalog to override? Prefer main panel for these.)
    skip_flags = {"-o", "--output", "-P", "--paths", "--cookies", "--cookies-from-browser"}

    for section in catalog.get("sections", []):
        for opt in section.get("options", []):
            oid = opt["id"]
            val = (option_values or {}).get(oid)
            otype = opt.get("type")
            primary = opt.get("primary") or (opt.get("flags") or [None])[0]
            flags = opt.get("flags") or []
            if any(f in skip_flags for f in flags):
                # Allow override only if user filled value and it's not the main ones we set
                if otype == "bool" and val:
                    pass  # rare for these
                else:
                    continue

            if otype == "bool":
                if val:
                    cmd.append(primary)
            elif otype == "preset":
                if val:
                    # val True means apply this preset name
                    cmd.extend(["-t", opt.get("preset_value", "")])
            elif otype in ("value", "choice"):
                if val is None or val == "":
                    continue
                if opt.get("multiple") and isinstance(val, list):
                    for item in val:
                        if item:
                            cmd.extend([primary, str(item)])
                else:
                    # Multi-token metavars (e.g. FIELDS REGEX REPLACE): split like a shell
                    metavar = opt.get("metavar") or ""
                    raw = str(val)
                    if " " in metavar.strip():
                        try:
                            parts = shlex.split(raw, posix=False)
                        except ValueError:
                            parts = raw.split()
                        if parts:
                            cmd.append(primary)
                            cmd.extend(parts)
                        else:
                            cmd.extend([primary, raw])
                    else:
                        cmd.extend([primary, raw])

    for url in urls:
        u = url.strip()
        if u:
            cmd.append(u)
    return cmd


def command_preview(argv: list[str]) -> str:
    return " ".join(_quote_preview(a) for a in argv)
