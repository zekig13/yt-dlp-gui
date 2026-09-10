"""Widgets for individual yt-dlp options."""
from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

OnChange = Callable[[], None]


class OptionRow(ctk.CTkFrame):
    """One option: checkbox (bool/preset) or checkbox+entry/combobox (value)."""

    def __init__(
        self,
        master,
        opt: dict[str, Any],
        *,
        on_change: OnChange | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.opt = opt
        self.on_change = on_change
        self._enabled = ctk.BooleanVar(value=False)
        self._value = ctk.StringVar(value="")

        otype = opt.get("type", "bool")
        flags = ", ".join(opt.get("flags", []))
        metavar = opt.get("metavar")
        label = flags
        if metavar and otype not in ("bool", "preset"):
            label = f"{flags} {metavar}"
        if otype == "preset":
            label = f"-t {opt.get('preset_value', '')}"

        self.columnconfigure(1, weight=1)

        self.chk = ctk.CTkCheckBox(
            self,
            text=label,
            variable=self._enabled,
            command=self._fire,
            font=ctk.CTkFont(size=12),
            width=280,
        )
        self.chk.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)

        self.entry: ctk.CTkEntry | ctk.CTkComboBox | None = None
        if otype in ("value", "choice"):
            choices = opt.get("choices")
            if otype == "choice" and choices:
                self.entry = ctk.CTkComboBox(
                    self,
                    values=list(choices),
                    variable=self._value,
                    width=220,
                    command=lambda _=None: self._fire(),
                )
            else:
                self.entry = ctk.CTkEntry(
                    self,
                    textvariable=self._value,
                    width=220,
                    placeholder_text=metavar or "değer",
                )
                self._value.trace_add("write", lambda *_: self._fire())
            self.entry.grid(row=0, column=1, sticky="ew", pady=2)
            self.entry.configure(state="disabled")

        help_txt = (opt.get("help") or "").strip()
        if help_txt:
            short = help_txt if len(help_txt) <= 160 else help_txt[:157] + "…"
            self.help_lbl = ctk.CTkLabel(
                self,
                text=short,
                anchor="w",
                justify="left",
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray65"),
                wraplength=720,
            )
            self.help_lbl.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(28, 0))

        self._enabled.trace_add("write", lambda *_: self._sync_entry_state())

    def _sync_entry_state(self) -> None:
        if self.entry is None:
            return
        state = "normal" if self._enabled.get() else "disabled"
        try:
            self.entry.configure(state=state)
        except Exception:
            pass

    def _fire(self) -> None:
        self._sync_entry_state()
        if self.on_change:
            self.on_change()

    def get_value(self) -> Any:
        otype = self.opt.get("type", "bool")
        if otype in ("bool", "preset"):
            return bool(self._enabled.get())
        if not self._enabled.get():
            return None
        return self._value.get()

    def set_value(self, value: Any) -> None:
        otype = self.opt.get("type", "bool")
        if otype in ("bool", "preset"):
            self._enabled.set(bool(value))
        elif value is None or value == "":
            self._enabled.set(False)
            self._value.set("")
        else:
            self._enabled.set(True)
            self._value.set(str(value))
        self._sync_entry_state()

    def matches_filter(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        blob = " ".join(
            [
                " ".join(self.opt.get("flags", [])),
                self.opt.get("help") or "",
                self.opt.get("metavar") or "",
                self.opt.get("preset_value") or "",
                self.opt.get("id") or "",
            ]
        ).lower()
        return q in blob


class SectionFrame(ctk.CTkFrame):
    """Collapsible-looking section with option rows."""

    def __init__(
        self,
        master,
        section: dict[str, Any],
        *,
        on_change: OnChange | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.section = section
        self.on_change = on_change
        self.rows: list[OptionRow] = []

        title = section.get("title_tr") or section.get("title") or ""
        eng = section.get("title") or ""
        header = f"{title}  ({eng})" if title != eng else title
        self.header = ctk.CTkLabel(
            self,
            text=header,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.header.pack(fill="x", padx=8, pady=(10, 4))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="x", padx=8, pady=(0, 8))

        for opt in section.get("options", []):
            row = OptionRow(self.body, opt, on_change=on_change)
            row.pack(fill="x", pady=1)
            self.rows.append(row)

    def collect(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for row in self.rows:
            val = row.get_value()
            if row.opt.get("type") in ("bool", "preset"):
                if val:
                    out[row.opt["id"]] = True
            elif val not in (None, ""):
                out[row.opt["id"]] = val
        return out

    def apply_values(self, values: dict[str, Any]) -> None:
        for row in self.rows:
            if row.opt["id"] in values:
                row.set_value(values[row.opt["id"]])

    def apply_filter(self, query: str) -> int:
        visible = 0
        for row in self.rows:
            if row.matches_filter(query):
                row.pack(fill="x", pady=1)
                visible += 1
            else:
                row.pack_forget()
        if visible:
            self.pack(fill="x", padx=4, pady=4)
        else:
            self.pack_forget()
        return visible
