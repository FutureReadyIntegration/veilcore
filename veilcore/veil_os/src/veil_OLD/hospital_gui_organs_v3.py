from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from .veil_organs_v2 import load_organs, list_organs, get_organ, filter_by_tier, label

VEIL_BIN = "/srv/veil_os/api_venv/bin/veil"

# --- Visual system (distinct from old gray UI) ---
C = {
    "bg": "#0B1220",          # deep navy background
    "panel": "#111B2E",       # panel background
    "panel2": "#0F172A",      # darker panel
    "border": "#22304A",      # borders
    "text": "#E6EEF9",        # primary text
    "muted": "#A9B7D0",       # muted text
    "accent": "#5B8CFF",      # primary accent
    "accent2": "#22C55E",     # success/ok
    "danger": "#EF4444",      # danger
    "warn": "#F59E0B",        # warning
    "chip": "#1B2A45",        # chip background
    "terminal": "#050914",    # output terminal background
    "terminal_text": "#C7D2FE",
}

F = {
    "h1": ("DejaVu Sans", 18, "bold"),
    "h2": ("DejaVu Sans", 13, "bold"),
    "b":  ("DejaVu Sans", 11, "bold"),
    "t":  ("DejaVu Sans", 11),
    "mono": ("DejaVu Sans Mono", 10),
}

ACTIONS = [
    ("Compile", "compile", False),
    ("Compile P0", "compile-p0", False),
    ("Compile All", "compile-all", True),
    ("Harden", "harden", True),
]

TIER_COLOR = {
    "P0": C["danger"],
    "P1": C["warn"],
    "P2": C["accent2"],
    "":   C["muted"],
}


class VeilHospitalGUIOrgansV3(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Veil OS — Hospital Command Center")
        self.geometry("1200x720")
        self.resizable(False, False)
        self.configure(bg=C["bg"])

        self.cmd_var = tk.StringVar(value="compile")
        self.target_var = tk.StringVar(value="")
        self.enable_writes = tk.BooleanVar(value=False)
        self.confirm_text = tk.StringVar(value="")

        self.tier_var = tk.StringVar(value="ALL")
        self.search_var = tk.StringVar(value="")

        load_organs()

        self._build_ui()
        self._refresh_organs_list()
        self._update_preview()
        self._set_status("PREVIEW mode (dry-run). Type YES + enable writes to apply.", ok=True)

    # ---------------- UI BUILD ----------------
    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=C["panel2"], highlightbackground=C["border"], highlightthickness=1)
        header.pack(fill="x", padx=12, pady=12)

        left = tk.Frame(header, bg=C["panel2"])
        left.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        tk.Label(left, text="VEIL OS", font=F["h1"], bg=C["panel2"], fg=C["text"]).pack(anchor="w")
        tk.Label(
            left,
            text="Hospital Command Center • Operator-safe workflows • Auditable actions",
            font=F["t"], bg=C["panel2"], fg=C["muted"]
        ).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(header, bg=C["panel2"])
        right.pack(side="right", padx=12, pady=10)

        self.mode_pill = tk.Label(
            right, text="MODE: PREVIEW", font=F["b"],
            bg=C["chip"], fg=C["text"], padx=12, pady=6
        )
        self.mode_pill.pack(anchor="e")

        # Body layout
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.col_left = tk.Frame(body, bg=C["bg"])
        self.col_left.pack(side="left", fill="y", padx=(0, 12))

        self.col_mid = tk.Frame(body, bg=C["bg"])
        self.col_mid.pack(side="left", fill="both", expand=True, padx=(0, 12))

        self.col_right = tk.Frame(body, bg=C["bg"])
        self.col_right.pack(side="right", fill="both", expand=True)

        self._panel_actions(self.col_left)
        self._panel_target(self.col_left)
        self._panel_safety(self.col_left)

        self._panel_organs(self.col_mid)
        self._panel_run(self.col_right)
        self._panel_output(self.col_right)

        # Status bar
        status = tk.Frame(self, bg=C["panel2"], highlightbackground=C["border"], highlightthickness=1)
        status.pack(fill="x", padx=12, pady=(0, 12))
        self.status_label = tk.Label(status, text="", font=F["t"], bg=C["panel2"], fg=C["muted"])
        self.status_label.pack(anchor="w", padx=12, pady=8)

    def _mk_panel(self, parent, title: str):
        p = tk.Frame(parent, bg=C["panel"], highlightbackground=C["border"], highlightthickness=1)
        tk.Label(p, text=title, font=F["h2"], bg=C["panel"], fg=C["text"]).pack(anchor="w", padx=12, pady=(10, 6))
        return p

    def _panel_actions(self, parent):
        p = self._mk_panel(parent, "Actions")
        p.pack(fill="x")

        for label_txt, cmd, _needs_target in ACTIONS:
            b = tk.Button(
                p, text=label_txt, font=F["b"],
                bg=C["accent"], fg="white",
                activebackground=C["accent"], activeforeground="white",
                relief="flat", padx=12, pady=10,
                command=lambda c=cmd: self._select_cmd(c),
                cursor="hand2",
            )
            b.pack(fill="x", padx=12, pady=6)

        hint = tk.Label(
            p,
            text="Tip: Compile All + Harden require a Target.",
            font=F["t"], bg=C["panel"], fg=C["muted"]
        )
        hint.pack(anchor="w", padx=12, pady=(6, 12))

    def _panel_target(self, parent):
        p = self._mk_panel(parent, "Target")
        p.pack(fill="x", pady=12)

        tk.Label(p, text="Service directory", font=F["t"], bg=C["panel"], fg=C["muted"]).pack(anchor="w", padx=12)
        e = tk.Entry(p, textvariable=self.target_var, font=F["t"], bg=C["panel2"], fg=C["text"],
                     insertbackground=C["text"], relief="flat")
        e.pack(fill="x", padx=12, pady=(6, 8), ipady=6)

        tk.Button(
            p, text="Browse…", font=F["b"],
            bg=C["chip"], fg=C["text"], relief="flat",
            command=self._browse, cursor="hand2",
            padx=12, pady=10,
        ).pack(fill="x", padx=12, pady=(0, 12))

    def _panel_safety(self, parent):
        p = self._mk_panel(parent, "Safety Gate")
        p.pack(fill="x")

        tk.Label(
            p,
            text="Preview is default. Apply requires:\n• Enable writes\n• Type YES",
            font=F["t"], bg=C["panel"], fg=C["muted"], justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        cb = tk.Checkbutton(
            p, text="Enable real writes",
            variable=self.enable_writes,
            bg=C["panel"], fg=C["text"],
            activebackground=C["panel"],
            selectcolor=C["panel2"],
            command=self._toggle_mode
        )
        cb.pack(anchor="w", padx=12, pady=(0, 8))

        tk.Label(p, text="Type YES to confirm", font=F["t"], bg=C["panel"], fg=C["muted"]).pack(anchor="w", padx=12)
        en = tk.Entry(p, textvariable=self.confirm_text, font=F["t"], bg=C["panel2"], fg=C["text"],
                      insertbackground=C["text"], relief="flat")
        en.pack(fill="x", padx=12, pady=(6, 12), ipady=6)

    def _panel_organs(self, parent):
        p = self._mk_panel(parent, "Organs (Service Modules)")
        p.pack(fill="both", expand=True)

        controls = tk.Frame(p, bg=C["panel"])
        controls.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(controls, text="Tier", font=F["t"], bg=C["panel"], fg=C["muted"]).pack(side="left")
        tier = tk.OptionMenu(controls, self.tier_var, "ALL", "P0", "P1", "P2", command=lambda *_: self._refresh_organs_list())
        tier.configure(bg=C["chip"], fg=C["text"], relief="flat", highlightthickness=0)
        tier["menu"].configure(bg=C["panel2"], fg=C["text"])
        tier.pack(side="left", padx=(8, 16))

        tk.Label(controls, text="Search", font=F["t"], bg=C["panel"], fg=C["muted"]).pack(side="left")
        s = tk.Entry(controls, textvariable=self.search_var, font=F["t"], bg=C["panel2"], fg=C["text"],
                     insertbackground=C["text"], relief="flat")
        s.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=6)
        s.bind("<KeyRelease>", lambda _e: self._refresh_organs_list())

        mid = tk.Frame(p, bg=C["panel"])
        mid.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Listbox
        lf = tk.Frame(mid, bg=C["panel"])
        lf.pack(side="left", fill="both", expand=True)

        self.organs_list = tk.Listbox(
            lf, font=F["t"], height=18,
            bg=C["panel2"], fg=C["text"],
            selectbackground=C["accent"], selectforeground="white",
            relief="flat", highlightthickness=1, highlightbackground=C["border"]
        )
        self.organs_list.pack(fill="both", expand=True)
        self.organs_list.bind("<<ListboxSelect>>", self._on_select_organ)

        # Details
        rf = tk.Frame(mid, bg=C["panel"])
        rf.pack(side="right", fill="both", expand=True, padx=(12, 0))

        tk.Label(rf, text="Details", font=F["h2"], bg=C["panel"], fg=C["text"]).pack(anchor="w")

        self.detail = ScrolledText(
            rf, font=F["mono"], height=18,
            bg=C["panel2"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", highlightthickness=1, highlightbackground=C["border"]
        )
        self.detail.pack(fill="both", expand=True, pady=(8, 0))
        self._set_detail("Select an organ to view glyph + affirmation.\n")

    def _panel_run(self, parent):
        p = self._mk_panel(parent, "Run")
        p.pack(fill="x")

        self.preview = tk.Label(
            p, text="", font=F["mono"],
            bg=C["panel"], fg=C["muted"], justify="left", anchor="w"
        )
        self.preview.pack(fill="x", padx=12, pady=(0, 8))

        btns = tk.Frame(p, bg=C["panel"])
        btns.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            btns, text="RUN", font=F["b"],
            bg=C["accent2"], fg="white",
            relief="flat", padx=14, pady=10,
            command=self._run, cursor="hand2",
        ).pack(side="right")

    def _panel_output(self, parent):
        p = self._mk_panel(parent, "Output")
        p.pack(fill="both", expand=True, pady=12)

        self.output = ScrolledText(
            p, font=F["mono"],
            bg=C["terminal"], fg=C["terminal_text"],
            insertbackground=C["terminal_text"],
            relief="flat", highlightthickness=1, highlightbackground=C["border"]
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ---------------- Behaviors ----------------
    def _set_status(self, msg: str, ok: bool = True) -> None:
        self.status_label.configure(text=msg, fg=C["muted"] if ok else C["danger"])

    def _select_cmd(self, cmd: str) -> None:
        self.cmd_var.set(cmd)
        self._update_preview()

    def _browse(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.target_var.set(d)
            self._update_preview()

    def _toggle_mode(self) -> None:
        if self.enable_writes.get():
            self.mode_pill.configure(text="MODE: APPLY", bg=C["danger"])
            self._set_status("APPLY mode enabled — requires YES confirmation.", ok=False)
        else:
            self.mode_pill.configure(text="MODE: PREVIEW", bg=C["chip"])
            self.confirm_text.set("")
            self._set_status("PREVIEW mode (dry-run). Safe to inspect changes.", ok=True)
        self._update_preview()

    def _build_cmd(self) -> list[str]:
        cmd = self.cmd_var.get()
        args = [VEIL_BIN, cmd]

        if cmd in {"compile-all", "harden"}:
            if not self.target_var.get():
                raise ValueError("Target required for compile-all/harden")
            args += ["--target", self.target_var.get()]

        # If your current veil CLI doesn't support these flags, tell me and
        # I'll generate a v4 GUI that matches your exact CLI signature.
        if self.enable_writes.get():
            if self.confirm_text.get() != "YES":
                raise ValueError("Type YES to apply")
            args += ["--yes"]
        else:
            args += ["--dry-run"]

        args += ["--no-input"]
        return args

    def _update_preview(self) -> None:
        try:
            self.preview.configure(text=" ".join(self._build_cmd()))
        except Exception as e:
            self.preview.configure(text=f"(incomplete) {e}")

    def _run(self) -> None:
        try:
            cmd = self._build_cmd()
        except Exception as e:
            messagebox.showerror("Blocked", str(e))
            return

        self.output.insert("end", "▶ " + " ".join(cmd) + "\n")
        self.output.see("end")

        def work():
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.stdout:
                self.output.insert("end", p.stdout)
            if p.stderr:
                self.output.insert("end", p.stderr)
            self.output.insert("end", f"\n⟡ exit={p.returncode}\n\n")
            self.output.see("end")

        threading.Thread(target=work, daemon=True).start()

    # ---------------- Organs ----------------
    def _refresh_organs_list(self) -> None:
        tier = self.tier_var.get().strip()
        search = self.search_var.get().strip().lower()

        if tier == "ALL":
            names = list_organs()
        else:
            names = filter_by_tier(tier)

        if search:
            names = [n for n in names if search in n.lower()]

        self.organs_list.delete(0, "end")
        for n in names:
            self.organs_list.insert("end", label(n))

    def _set_detail(self, text: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", text)
        self.detail.configure(state="disabled")

    def _on_select_organ(self, _evt=None) -> None:
        sel = self.organs_list.curselection()
        if not sel:
            return
        display = self.organs_list.get(sel[0])
        # "⚡ epic (P0)" -> name between first space and last " ("
        name_part = display.split(" ", 1)[1] if " " in display else display
        name = name_part.split(" (", 1)[0].strip()

        obj = get_organ(name) or {}
        nm = obj.get("name", name)
        tier = obj.get("tier", "")
        glyph = obj.get("glyph", "")
        aff = obj.get("affirmation", "")

        tier_color = TIER_COLOR.get(tier, C["muted"])

        self._set_detail(
            f"{glyph}  {nm}\n"
            f"TIER: {tier}\n\n"
            f"AFFIRMATION:\n{aff}\n"
        )
        self._set_status(f"Selected {nm} [{tier}]", ok=True)


def main() -> None:
    VeilHospitalGUIOrgansV3().mainloop()
