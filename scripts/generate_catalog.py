#!/usr/bin/env python3
"""Parse yt-dlp --help text into app/options_catalog.json."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HELP = ROOT / "yt-dlp-help.txt"
DEFAULT_OUT = ROOT / "app" / "options_catalog.json"

SECTION_RE = re.compile(r"^  ([A-Za-z][\w /()-]+):\s*$")
FLAG_RE = re.compile(r"(?:^|,\s*)(-[\w]+|--[\w-]+)")
CONT_RE = re.compile(r"^ {36,}\S")  # continuation of description

# Turkish section titles (fallback: keep English)
SECTION_TR = {
    "General Options": "Genel Seçenekler",
    "Network Options": "Ağ Seçenekleri",
    "Geo-restriction": "Coğrafi Kısıtlama",
    "Video Selection": "Video Seçimi",
    "Download Options": "İndirme Seçenekleri",
    "Filesystem Options": "Dosya Sistemi Seçenekleri",
    "Thumbnail Options": "Küçük Resim Seçenekleri",
    "Internet Shortcut Options": "İnternet Kısayolu Seçenekleri",
    "Verbosity and Simulation Options": "Ayrıntı ve Simülasyon",
    "Workarounds": "Geçici Çözümler",
    "Video Format Options": "Video Biçimi Seçenekleri",
    "Subtitle Options": "Altyazı Seçenekleri",
    "Authentication Options": "Kimlik Doğrulama",
    "Post-Processing Options": "Son İşleme Seçenekleri",
    "SponsorBlock Options": "SponsorBlock Seçenekleri",
    "Extractor Options": "Çıkarıcı Seçenekleri",
    "Preset Aliases": "Hazır Kısayollar",
}

# Options already covered on the main panel (still in catalog, but tagged)
MAIN_PANEL = {
    "--format",
    "-f",
    "--output",
    "-o",
    "--paths",
    "-P",
    "--cookies",
    "--cookies-from-browser",
}


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "option"


def parse_left(left: str) -> tuple[list[str], str | None]:
    flags = FLAG_RE.findall(left)
    rest = left
    for f in flags:
        rest = re.sub(r"(^|,\s*)" + re.escape(f), r"\1", rest, count=1)
    rest = rest.replace(",", " ").strip()
    rest = re.sub(r"\s+", " ", rest)
    return flags, (rest or None)


def option_id(flags: list[str]) -> str:
    primary = next((f for f in flags if f.startswith("--")), flags[0] if flags else "opt")
    return primary.lstrip("-").replace("-", "_")


def detect_choices(help_text: str, metavar: str | None) -> list[str] | None:
    """Heuristic: extract quoted choice lists from help when short."""
    if not help_text:
        return None
    # e.g. One of "default", "never", ...
    m = re.search(
        r'(?:one of|either)\s+((?:"[^"]+"|\'[^\']+\')(?:\s*,\s*(?:or\s+)?(?:"[^"]+"|\'[^\']+\'))+)',
        help_text,
        re.I,
    )
    if m:
        choices = re.findall(r'["\']([^"\']+)["\']', m.group(1))
        if 2 <= len(choices) <= 12:
            return choices
    return None


def parse_help(text: str) -> dict:
    lines = text.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        sm = SECTION_RE.match(line)
        if sm:
            title = sm.group(1)
            current = {
                "id": slugify(title),
                "title": title,
                "title_tr": SECTION_TR.get(title, title),
                "options": [],
            }
            sections.append(current)
            i += 1
            continue

        # Preset alias lines: "    -t mp3                          ..."
        if current and current["title"] == "Preset Aliases":
            pm = re.match(r"^    -t\s+(\S+)\s{2,}(.*)$", line)
            if pm:
                name, desc = pm.group(1), pm.group(2).strip()
                j = i + 1
                while j < len(lines) and CONT_RE.match(lines[j]):
                    desc = (desc + " " + lines[j].strip()).strip()
                    j += 1
                current["options"].append(
                    {
                        "id": f"preset_{name}",
                        "flags": ["-t", "--preset-alias"],
                        "primary": "-t",
                        "metavar": "NAME",
                        "type": "preset",
                        "preset_value": name,
                        "help": desc,
                        "multiple": False,
                        "main_panel": False,
                    }
                )
                i = j
                continue

        if line.startswith("    -") and current is not None:
            m = re.match(r"^    (.+?)(?:\s{2,}(.*))?$", line)
            if not m:
                i += 1
                continue
            left, desc = m.group(1).strip(), (m.group(2) or "").strip()
            j = i + 1
            while j < len(lines) and CONT_RE.match(lines[j]):
                desc = (desc + " " + lines[j].strip()).strip()
                j += 1
            flags, metavar = parse_left(left)
            if not flags:
                i = j
                continue
            # Skip duplicate preset parsing under other sections
            opt_type = "bool" if not metavar else "value"
            primary = next((f for f in flags if f.startswith("--")), flags[0])
            multi = bool(
                re.search(r"can be used multiple times|multiple times", desc, re.I)
            )
            choices = detect_choices(desc, metavar) if opt_type == "value" else None
            entry = {
                "id": option_id(flags),
                "flags": flags,
                "primary": primary,
                "metavar": metavar,
                "type": opt_type,
                "help": desc,
                "multiple": multi,
                "main_panel": any(f in MAIN_PANEL for f in flags),
            }
            if choices:
                entry["choices"] = choices
                entry["type"] = "choice"
            current["options"].append(entry)
            i = j
            continue

        i += 1

    # Deduplicate option ids within a section by appending index
    for sec in sections:
        seen: dict[str, int] = {}
        for opt in sec["options"]:
            oid = opt["id"]
            if oid in seen:
                seen[oid] += 1
                opt["id"] = f"{oid}_{seen[oid]}"
            else:
                seen[oid] = 0

    total = sum(len(s["options"]) for s in sections)
    return {
        "source": "yt-dlp --help",
        "option_count": total,
        "section_count": len(sections),
        "sections": sections,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate yt-dlp options catalog JSON")
    ap.add_argument("--help-file", type=Path, default=DEFAULT_HELP)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.help_file.is_file():
        print(f"Help file not found: {args.help_file}", file=sys.stderr)
        return 1
    text = args.help_file.read_text(encoding="utf-8", errors="replace")
    catalog = parse_help(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {args.output} — {catalog['option_count']} options in "
        f"{catalog['section_count']} sections"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
