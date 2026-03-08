from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from .veil_organs import load_organs, list_organs, get_organ, filter_by_tier, label

VEIL_BIN = "/srv/veil_os/api_venv/bin/veil"

COLORS = {
    "bg": "#F7FAFC",
    "panel": "#FFFFFF",
    "text": "#0B1220",
    "muted": "#5B677A",
    "border": "#D8E1EA",
    "primary": "#1F6FEB",
    "primary_dark": "#174EA6",
    "danger": "#B42318",
    "success": "#0E9384",
}

FONT = ("DejaVu Sans", 11)
FONT_B = ("DejaVu Sans", 11, "bold")
FONT_H = ("DejaVu Sans", 16, "bold")
FONT_M = ("DejaVu Sans Mono", 10)

ACTIONS = [
    ("Compile", "compile", False),
    ("Compile P0", "compile-p0", False),
    ("Compile All", "compile-all", True),
    ("Harden", "harden", True),
]


class VeilHospitalGUIOrgans(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Veil OS Organ Engine — Hospital GUI")
        self.geometry("1120x680")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        self.cmd_var = tk.StringVar(value="compile")
        self.target_var = tk.StringVar(value="")
        self.enable_writes = tk.BooleanVar(value=False)
        self.confirm_text = tk.StringVar(value="")

        self.tier_var = tk.StringVar(value="ALL")
        self.search_var = tk.StringVar(value="")

        load_organs()  # loads /opt/veil_os/data/organs.json

        self._build_ui()
        self._update_preview()
        self._refresh_organs_list()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        header.pack(fill="x", padx=12, pady=12)

        tk.Label(header, text="Veil OS Organ Engine", font=FONT_H, bg=COLORS["panel"], fg=COLORS["text"]).pack(
            anchor="w", padx=12, pady=(10, 0)
        )
        tk.Label(
            header,
            text="Hospital Mode — Preview by default. Real changes require explicit confirmation.",
            font=FONT,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12, pady=(0, 10))

        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        left = tk.Frame(main, bg=COLORS["bg"])
        left.pack(side="left", fill="y", padx=(0, 12))

        center = tk.Frame(main, bg=COLORS["bg"])
        center.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(main, bg=COLORS["bg"])
        right.pack(side="right", fill="both", expand=True)

        self._build_actions(left)
        self._build_target(left)
        self._build_safety(left)

        self._build_organs(center)
        self._build_run_panel(right)
        self._build_output(right)

    def _build_actions(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="x")
        tk.Label(box, text="Actions", font=FONT_B, bg=COLORS["panel"]).pack(anchor="w", padx=12, pady=10)

        for label_txt, cmd, _ in ACTIONS:
            tk.Button(
                box,
                text=label_txt,
                font=FONT_B,
                bg=COLORS["primary"],
                fg="white",
                activebackground=COLORS["primary_dark"],
                relief="flat",
                command=lambda c=cmd: self._select_cmd(c),
                padx=12,
                pady=10,
            ).pack(fill="x", padx=12, pady=6)

    def _build_target(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="x", pady=12)

        tk.Label(box, text="Target Directory", font=FONT_B, bg=COLORS["panel"]).pack(anchor="w", padx=12, pady=6)
        tk.Entry(box, textvariable=self.target_var, font=FONT).pack(fill="x", padx=12)
        tk.Button(box, text="Browse…", font=FONT_B, bg=COLORS["panel"], fg=COLORS["primary"], command=self._browse).pack(
            fill="x", padx=12, pady=10
        )

    def _build_safety(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="x")

        self.mode_label = tk.Label(box, text="MODE: PREVIEW (dry-run)", bg=COLORS["success"], fg="white", font=FONT_B, pady=6)
        self.mode_label.pack(fill="x", padx=12, pady=10)

        tk.Checkbutton(
            box,
            text="Enable real writes",
            variable=self.enable_writes,
            bg=COLORS["panel"],
            command=self._toggle_mode,
        ).pack(anchor="w", padx=12)

        tk.Label(box, text="Type YES to confirm:", bg=COLORS["panel"], fg=COLORS["muted"]).pack(anchor="w", padx=12, pady=(6, 0))
        tk.Entry(box, textvariable=self.confirm_text, font=FONT).pack(fill="x", padx=12, pady=(0, 10))

    def _build_organs(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="Organs (Service Modules)", font=FONT_B, bg=COLORS["panel"]).pack(anchor="w", padx=12, pady=(10, 6))

        controls = tk.Frame(box, bg=COLORS["panel"])
        controls.pack(fill="x", padx=12)

        tk.Label(controls, text="Tier:", bg=COLORS["panel"], fg=COLORS["muted"]).pack(side="left")
        tier = tk.OptionMenu(controls, self.tier_var, "ALL", "P0", "P1", "P2", command=lambda *_: self._refresh_organs_list())
        tier.config(bg=COLORS["panel"])
        tier.pack(side="left", padx=(6, 12))

        tk.Label(controls, text="Search:", bg=COLORS["panel"], fg=COLORS["muted"]).pack(side="left")
        search = tk.Entry(controls, textvariable=self.search_var, font=FONT)
        search.pack(side="left", fill="x", expand=True, padx=(6, 0))
        search.bind("<KeyRelease>", lambda _e: self._refresh_organs_list())

        mid = tk.Frame(box, bg=COLORS["panel"])
        mid.pack(fill="both", expand=True, padx=12, pady=12)

        list_frame = tk.Frame(mid, bg=COLORS["panel"])
        list_frame.pack(side="left", fill="both", expand=True)

        self.organs_list = tk.Listbox(list_frame, font=FONT, height=18)
        self.organs_list.pack(fill="both", expand=True)
        self.organs_list.bind("<<ListboxSelect>>", self._on_select_organ)

        detail_frame = tk.Frame(mid, bg=COLORS["panel"])
        detail_frame.pack(side="right", fill="both", expand=True, padx=(12, 0))

        tk.Label(detail_frame, text="Details", font=FONT_B, bg=COLORS["panel"]).pack(anchor="w")
        self.org_detail = ScrolledText(detail_frame, font=FONT_M, height=18)
        self.org_detail.pack(fill="both", expand=True, pady=(6, 0))
        self._set_detail("Select an organ to view glyph + affirmation.\n")

    def _build_run_panel(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="x")

        self.preview = tk.Label(box, text="", font=FONT_M, bg=COLORS["panel"], fg=COLORS["muted"], anchor="w", justify="left")
        self.preview.pack(fill="x", padx=12, pady=10)

        tk.Button(box, text="RUN", font=FONT_B, bg=COLORS["primary"], fg="white", command=self._run, padx=16, pady=10).pack(
            side="right", padx=12, pady=10
        )

    def _build_output(self, parent):
        box = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        box.pack(fill="both", expand=True, pady=12)

        self.output = ScrolledText(box, font=FONT_M)
        self.output.pack(fill="both", expand=True, padx=12, pady=12)

    # ---------------- Actions ----------------
    def _select_cmd(self, cmd):
        self.cmd_var.set(cmd)
        self._update_preview()

    def _browse(self):
        d = filedialog.askdirectory()
        if d:
            self.target_var.set(d)
            self._update_preview()

    def _toggle_mode(self):
        if self.enable_writes.get():
            self.mode_label.config(text="MODE: APPLY (real writes)", bg=COLORS["danger"])
        else:
            self.mode_label.config(text="MODE: PREVIEW (dry-run)", bg=COLORS["success"])
            self.confirm_text.set("")
        self._update_preview()

    def _build_cmd(self):
        cmd = self.cmd_var.get()
        args = [VEIL_BIN, cmd]

        if cmd in {"compile-all", "harden"}:
            if not self.target_var.get():
                raise ValueError("Target required")
            args += ["--target", self.target_var.get()]

        # NOTE: This assumes your Veil CLI supports --dry-run/--yes/--no-input.
        # If it doesn't (yet), we can adjust GUI-run args safely.
        if self.enable_writes.get():
            if self.confirm_text.get() != "YES":
                raise ValueError("Type YES to apply")
            args += ["--yes"]
        else:
            args += ["--dry-run"]

        args += ["--no-input"]
        return args

    def _update_preview(self):
        try:
            self.preview.config(text=" ".join(self._build_cmd()))
        except Exception as e:
            self.preview.config(text=f"(incomplete) {e}")

    def _run(self):
        try:
            cmd = self._build_cmd()
        except Exception as e:
            messagebox.showerror("Blocked", str(e))
            return

        self.output.insert("end", "Running: " + " ".join(cmd) + "\n")
        self.output.see("end")

        def work():
            p = subprocess.run(cmd, capture_output=True, text=True)
            self.output.insert("end", p.stdout + p.stderr)
            self.output.insert("end", f"\nExit code: {p.returncode}\n")
            self.output.see("end")

        threading.Thread(target=work, daemon=True).start()

    # ---------------- Organs ----------------
    def _refresh_organs_list(self):
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

    def _set_detail(self, text: str):
        self.org_detail.configure(state="normal")
        self.org_detail.delete("1.0", "end")
        self.org_detail.insert("end", text)
        self.org_detail.configure(state="disabled")

    def _on_select_organ(self, _evt=None):
        sel = self.organs_list.curselection()
        if not sel:
            return

        display = self.organs_list.get(sel[0])

        # display is like "⚡ epic (P0)" — extract name by splitting
        # safest: find the first space, then strip trailing " (PX)"
        parts = display.split(" ", 1)
        name_part = parts[1] if len(parts) == 2 else display
        name = name_part.split(" (", 1)[0].strip()

        obj = get_organ(name) or {}
        glyph = obj.get("glyph", "")
        tier = obj.get("tier", "")
        aff = obj.get("affirmation", "")

        self._set_detail(
            f"Name: {obj.get('name', name)}\n"
            f"Tier: {tier}\n"
            f"Glyph: {glyph}\n\n"
            f"Affirmation:\n{aff}\n"
        )


def main() -> None:
    VeilHospitalGUIOrgans().mainloop()
