"""Main CustomTkinter window for yt-dlp GUI."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from app.catalog import load_catalog
from app.command_builder import build_command, command_preview
from app.runner import DownloadRunner
from app.settings import load_settings, save_settings
from app.ui.option_widgets import SectionFrame

FORMAT_LABELS = [
    ("best", "En iyi (bv*+ba/b)"),
    ("bestvideo+bestaudio", "bestvideo+bestaudio"),
    ("mp4", "MP4 tercih"),
    ("webm", "WebM tercih"),
    ("audio-best", "Sadece ses (best)"),
    ("mp3", "MP3 ses"),
    ("m4a", "M4A ses"),
    ("worst", "En düşük"),
    ("custom", "Özel (-f panelden)"),
]


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("yt-dlp GUI — İndirici")
        self.minsize(960, 640)

        self.settings = load_settings()
        self.catalog = load_catalog()
        self.runner = DownloadRunner()
        self._section_frames: list[SectionFrame] = []
        self._preview_after: str | None = None

        geo = self.settings.get("window_geometry") or "1100x780"
        try:
            self.geometry(geo)
        except tk.TclError:
            self.geometry("1100x780")

        mode = self.settings.get("appearance_mode") or "System"
        theme = self.settings.get("color_theme") or "blue"
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme(theme)

        self._build_ui()
        self._load_into_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._update_preview)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top: main controls ---
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        top.grid_columnconfigure(1, weight=1)

        r = 0
        ctk.CTkLabel(top, text="URL(ler)", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="nw", padx=6, pady=4
        )
        self.urls_text = ctk.CTkTextbox(top, height=70)
        self.urls_text.grid(row=r, column=1, columnspan=2, sticky="ew", padx=6, pady=4)
        self.urls_text.bind("<KeyRelease>", lambda e: self._schedule_preview())

        r = 1
        ctk.CTkLabel(top, text="Çıktı klasörü\n(-P home:)").grid(
            row=r, column=0, sticky="w", padx=6, pady=4
        )
        self.output_dir_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self.output_dir_var).grid(
            row=r, column=1, sticky="ew", padx=6, pady=4
        )
        ctk.CTkButton(top, text="Gözat…", width=90, command=self._browse_outdir).grid(
            row=r, column=2, padx=6, pady=4
        )
        self.output_dir_var.trace_add("write", lambda *_: self._schedule_preview())

        r = 2
        ctk.CTkLabel(top, text="Çıktı şablonu\n(-o)").grid(
            row=r, column=0, sticky="w", padx=6, pady=4
        )
        self.output_tmpl_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self.output_tmpl_var).grid(
            row=r, column=1, columnspan=2, sticky="ew", padx=6, pady=4
        )
        self.output_tmpl_var.trace_add("write", lambda *_: self._schedule_preview())

        r = 3
        ctk.CTkLabel(top, text="Biçim kısayolu\n(-f)").grid(
            row=r, column=0, sticky="w", padx=6, pady=4
        )
        self.format_var = ctk.StringVar(value="best")
        fmt_values = [f"{k} — {lab}" for k, lab in FORMAT_LABELS]
        self._fmt_map = {f"{k} — {lab}": k for k, lab in FORMAT_LABELS}
        self._fmt_rev = {k: f"{k} — {lab}" for k, lab in FORMAT_LABELS}
        self.format_combo = ctk.CTkComboBox(
            top,
            values=fmt_values,
            command=lambda _: self._schedule_preview(),
            width=320,
        )
        self.format_combo.grid(row=r, column=1, sticky="w", padx=6, pady=4)

        r = 4
        ctk.CTkLabel(top, text="Çerezler\n(--cookies)").grid(
            row=r, column=0, sticky="w", padx=6, pady=4
        )
        self.cookies_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self.cookies_var).grid(
            row=r, column=1, sticky="ew", padx=6, pady=4
        )
        ctk.CTkButton(top, text="Gözat…", width=90, command=self._browse_cookies).grid(
            row=r, column=2, padx=6, pady=4
        )
        self.cookies_var.trace_add("write", lambda *_: self._schedule_preview())

        r = 5
        ctk.CTkLabel(top, text="yt-dlp yolu").grid(
            row=r, column=0, sticky="w", padx=6, pady=4
        )
        self.ytdlp_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self.ytdlp_var).grid(
            row=r, column=1, sticky="ew", padx=6, pady=4
        )
        ctk.CTkButton(top, text="Gözat…", width=90, command=self._browse_ytdlp).grid(
            row=r, column=2, padx=6, pady=4
        )
        self.ytdlp_var.trace_add("write", lambda *_: self._schedule_preview())

        # --- Notebook: options + log ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        self.tabs.add("Tüm Seçenekler")
        self.tabs.add("Komut & Log")

        opt_tab = self.tabs.tab("Tüm Seçenekler")
        opt_tab.grid_columnconfigure(0, weight=1)
        opt_tab.grid_rowconfigure(1, weight=1)

        search_row = ctk.CTkFrame(opt_tab, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", pady=(4, 4))
        search_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(search_row, text="Ara:").grid(row=0, column=0, padx=(0, 6))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            placeholder_text="bayrak, açıklama veya bölüm…",
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_var.trace_add("write", lambda *_: self._apply_search())
        self.search_count = ctk.CTkLabel(search_row, text="")
        self.search_count.grid(row=0, column=2, padx=8)

        self.options_scroll = ctk.CTkScrollableFrame(opt_tab)
        self.options_scroll.grid(row=1, column=0, sticky="nsew")
        self.options_scroll.grid_columnconfigure(0, weight=1)

        for section in self.catalog.get("sections", []):
            sf = SectionFrame(
                self.options_scroll, section, on_change=self._schedule_preview
            )
            sf.pack(fill="x", padx=4, pady=4)
            self._section_frames.append(sf)

        nopt = self.catalog.get("option_count", 0)
        self.search_count.configure(text=f"{nopt} seçenek")

        # Log tab
        log_tab = self.tabs.tab("Komut & Log")
        self._rebuild_log_tab(log_tab)

        # --- Bottom buttons ---
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(4, 10))
        bottom.grid_columnconfigure(4, weight=1)

        self.btn_run = ctk.CTkButton(
            bottom, text="İndirmeyi Başlat", width=140, command=self._start_download
        )
        self.btn_run.grid(row=0, column=0, padx=4)
        self.btn_cancel = ctk.CTkButton(
            bottom,
            text="İptal (süreç ağacı)",
            width=150,
            fg_color="#a33",
            hover_color="#822",
            command=self._cancel_download,
            state="disabled",
        )
        self.btn_cancel.grid(row=0, column=1, padx=4)
        ctk.CTkButton(bottom, text="Ayarları Kaydet", width=120, command=self._save).grid(
            row=0, column=2, padx=4
        )
        ctk.CTkButton(
            bottom, text="Önizlemeyi Kopyala", width=140, command=self._copy_preview
        ).grid(row=0, column=3, padx=4)
        self.status_var = ctk.StringVar(value="Hazır")
        ctk.CTkLabel(bottom, textvariable=self.status_var, anchor="e").grid(
            row=0, column=4, sticky="e", padx=8
        )

    def _rebuild_log_tab(self, log_tab) -> None:
        for child in log_tab.winfo_children():
            child.destroy()
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(1, weight=1)

        prev_frame = ctk.CTkFrame(log_tab, fg_color="transparent")
        prev_frame.grid(row=0, column=0, sticky="ew", pady=(4, 4))
        prev_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            prev_frame, text="Komut önizleme (canlı)", font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.preview_box = ctk.CTkTextbox(prev_frame, height=110, wrap="word")
        self.preview_box.grid(row=1, column=0, sticky="ew", pady=4)

        log_inner = ctk.CTkFrame(log_tab, fg_color="transparent")
        log_inner.grid(row=1, column=0, sticky="nsew")
        log_inner.grid_columnconfigure(0, weight=1)
        log_inner.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            log_inner, text="Çıktı günlüğü", font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.log_box = ctk.CTkTextbox(log_inner, wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", pady=4)

    # -------------------------------------------------------------- helpers
    def _browse_outdir(self) -> None:
        path = filedialog.askdirectory(title="Çıktı klasörü")
        if path:
            self.output_dir_var.set(path)

    def _browse_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="cookies.txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if path:
            self.cookies_var.set(path)

    def _browse_ytdlp(self) -> None:
        path = filedialog.askopenfilename(
            title="yt-dlp.exe",
            filetypes=[
                ("Executable", "*.exe"),
                ("All", "*.*"),
            ],
        )
        if path:
            self.ytdlp_var.set(path)

    def _load_into_ui(self) -> None:
        s = self.settings
        self.urls_text.delete("1.0", "end")
        self.urls_text.insert("1.0", s.get("urls") or "")
        self.output_dir_var.set(s.get("output_dir") or "")
        self.output_tmpl_var.set(s.get("output_template") or "")
        self.cookies_var.set(s.get("cookies_path") or "")
        self.ytdlp_var.set(s.get("ytdlp_path") or "")
        key = s.get("format_shortcut") or "best"
        self.format_combo.set(self._fmt_rev.get(key, self._fmt_rev["best"]))
        opt_vals = s.get("option_values") or {}
        for sf in self._section_frames:
            sf.apply_values(opt_vals)

    def _collect_option_values(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for sf in self._section_frames:
            out.update(sf.collect())
        return out

    def _format_key(self) -> str:
        raw = self.format_combo.get()
        return self._fmt_map.get(raw, "best")

    def _urls_list(self) -> list[str]:
        text = self.urls_text.get("1.0", "end")
        urls = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # allow space-separated on one line
            urls.extend(line.split())
        return urls

    def _current_argv(self) -> list[str]:
        return build_command(
            ytdlp_path=self.ytdlp_var.get().strip(),
            urls=self._urls_list(),
            output_dir=self.output_dir_var.get().strip(),
            output_template=self.output_tmpl_var.get().strip(),
            format_shortcut=self._format_key(),
            cookies_path=self.cookies_var.get().strip(),
            option_values=self._collect_option_values(),
            catalog=self.catalog,
        )

    def _schedule_preview(self) -> None:
        if self._preview_after:
            try:
                self.after_cancel(self._preview_after)
            except Exception:
                pass
        self._preview_after = self.after(150, self._update_preview)

    def _update_preview(self) -> None:
        self._preview_after = None
        try:
            argv = self._current_argv()
            text = command_preview(argv)
        except Exception as exc:
            text = f"# önizleme hatası: {exc}"
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", text)
        self.preview_box.configure(state="disabled")

    def _apply_search(self) -> None:
        q = self.search_var.get().strip()
        total = 0
        for sf in self._section_frames:
            total += sf.apply_filter(q)
        self.search_count.configure(text=f"{total} eşleşme" if q else f"{self.catalog.get('option_count', 0)} seçenek")

    def _append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _copy_preview(self) -> None:
        text = self.preview_box.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Komut panoya kopyalandı")

    def _gather_settings(self) -> dict[str, Any]:
        return {
            "ytdlp_path": self.ytdlp_var.get().strip(),
            "cookies_path": self.cookies_var.get().strip(),
            "output_dir": self.output_dir_var.get().strip(),
            "output_template": self.output_tmpl_var.get().strip(),
            "format_shortcut": self._format_key(),
            "urls": self.urls_text.get("1.0", "end").rstrip("\n"),
            "window_geometry": self.geometry(),
            "appearance_mode": self.settings.get("appearance_mode") or "System",
            "color_theme": self.settings.get("color_theme") or "blue",
            "option_values": self._collect_option_values(),
        }

    def _save(self) -> None:
        data = self._gather_settings()
        save_settings(data)
        self.settings = data
        self.status_var.set(f"Kaydedildi: ayarlar")

    def _on_close(self) -> None:
        try:
            save_settings(self._gather_settings())
        except OSError:
            pass
        if self.runner.is_running:
            if not messagebox.askyesno(
                "Çıkış",
                "İndirme sürüyor. Süreci öldürüp çıkılsın mı?",
            ):
                return
            self.runner.cancel()
        self.destroy()

    # ----------------------------------------------------------- run/cancel
    def _start_download(self) -> None:
        if self.runner.is_running:
            messagebox.showwarning("Uyarı", "Zaten bir indirme çalışıyor.")
            return
        ytdlp = self.ytdlp_var.get().strip()
        if not ytdlp:
            messagebox.showerror("Hata", "yt-dlp yolu boş.")
            return
        if not Path(ytdlp).is_file():
            if not messagebox.askyesno(
                "yt-dlp bulunamadı",
                f"Dosya yok:\n{ytdlp}\n\nYine de çalıştırmayı dene?",
            ):
                return
        urls = self._urls_list()
        if not urls:
            messagebox.showerror("Hata", "En az bir URL girin.")
            return

        argv = self._current_argv()
        self.tabs.set("Komut & Log")
        self._update_preview()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._append_log("$ " + command_preview(argv))
        self._append_log("—")

        self.btn_run.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.status_var.set("İndiriliyor…")

        cwd = self.output_dir_var.get().strip() or None
        if cwd and not Path(cwd).is_dir():
            try:
                Path(cwd).mkdir(parents=True, exist_ok=True)
            except OSError:
                cwd = None

        def on_line(line: str) -> None:
            self.after(0, lambda l=line: self._append_log(l))

        def on_done(code: int | None) -> None:
            self.after(0, lambda: self._download_finished(code))

        try:
            self.runner.start(argv, on_line=on_line, on_done=on_done, cwd=cwd)
        except Exception as exc:
            self.btn_run.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            self.status_var.set("Hata")
            messagebox.showerror("Başlatılamadı", str(exc))

    def _download_finished(self, code: int | None) -> None:
        self.btn_run.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        if code == 0:
            self.status_var.set("Tamamlandı (0)")
            self._append_log(f"\n[çıkış kodu: {code}]")
        else:
            self.status_var.set(f"Bitti (kod {code})")
            self._append_log(f"\n[çıkış kodu: {code}]")

    def _cancel_download(self) -> None:
        if not self.runner.is_running:
            return
        self._append_log("\n[iptal — taskkill /F /T …]")
        self.runner.cancel()
        self.status_var.set("İptal istendi")


def run_app() -> None:
    # On headless / no DISPLAY, CustomTkinter may fail — caller handles.
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    run_app()
