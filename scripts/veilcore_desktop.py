#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk, messagebox
from urllib import request

APP_TITLE = "VeilCore Desktop"
DEFAULT_API = os.environ.get("VEIL_API", "http://127.0.0.1:9444")

C = {
    "bg": "#071018",
    "bg2": "#0c1824",
    "bg3": "#122434",
    "panel": "#0e1b29",
    "panel2": "#13283b",
    "cyan": "#00e5ff",
    "cyan2": "#67f3ff",
    "green": "#00ff88",
    "gold": "#fbbf24",
    "orange": "#ff8c42",
    "red": "#ff5470",
    "purple": "#9b7bff",
    "text": "#e8fbff",
    "text2": "#9fc7d3",
    "dim": "#5f7d8a",
    "line": "#1b3950",
    "black": "#05080d",
}


def api_get(base: str, path: str, timeout: float = 3.0) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    req = request.Request(url)
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def api_post(base: str, path: str, payload: dict, timeout: float = 3.0) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def derive_engines_from_events(events: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for ev in events:
        et = str(ev.get("type", ""))
        payload = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
        name = payload.get("name")
        if not name:
            continue
        if not et.startswith("engine."):
            continue
        latest[str(name)] = {
            "id": str(ev.get("source") or str(name).lower()),
            "name": str(name),
            "state": str(payload.get("state", "unknown")),
            "health": payload.get("health", "--"),
            "service": str(payload.get("service", "")),
            "last_error": str(payload.get("last_error", ev.get("message", ""))),
            "updated_at": str(payload.get("updated_at", ev.get("ts", ""))),
        }
    return list(latest.values())


@dataclass
class GlobalState:
    api_base_url: str = DEFAULT_API

    def api_base(self) -> str:
        return self.api_base_url


def apply_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=C["bg"])

    style.configure(".", background=C["bg"], foreground=C["text"], fieldbackground=C["bg2"])
    style.configure("TFrame", background=C["bg"])
    style.configure("Panel.TFrame", background=C["panel"])
    style.configure("Card.TFrame", background=C["panel2"])
    style.configure("TLabel", background=C["bg"], foreground=C["text"])
    style.configure("Panel.TLabel", background=C["panel"], foreground=C["text"])
    style.configure("Card.TLabel", background=C["panel2"], foreground=C["text"])
    style.configure("Dim.TLabel", background=C["bg"], foreground=C["dim"])
    style.configure("Title.TLabel", background=C["bg"], foreground=C["cyan"], font=("Segoe UI", 18, "bold"))
    style.configure("Section.TLabel", background=C["bg"], foreground=C["gold"], font=("Segoe UI", 11, "bold"))
    style.configure("MetricValue.TLabel", background=C["panel2"], foreground=C["cyan2"], font=("Segoe UI", 20, "bold"))
    style.configure("MetricLabel.TLabel", background=C["panel2"], foreground=C["text2"], font=("Segoe UI", 9, "bold"))

    style.configure(
        "TButton",
        background=C["bg3"],
        foreground=C["text"],
        bordercolor=C["line"],
        lightcolor=C["bg3"],
        darkcolor=C["bg3"],
        padding=8,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", C["panel2"])],
        foreground=[("active", C["cyan2"])],
        bordercolor=[("active", C["cyan"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=C["bg2"],
        foreground=C["text"],
        bordercolor=C["line"],
        insertcolor=C["cyan"],
        padding=6,
    )

    style.configure("TNotebook", background=C["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=C["bg3"],
        foreground=C["text2"],
        padding=(14, 8),
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", C["panel2"]), ("active", C["bg3"])],
        foreground=[("selected", C["cyan"]), ("active", C["text"])],
    )

    style.configure(
        "Treeview",
        background=C["panel"],
        foreground=C["text"],
        fieldbackground=C["panel"],
        bordercolor=C["line"],
        rowheight=26,
        font=("Consolas", 10),
    )
    style.configure(
        "Treeview.Heading",
        background=C["bg3"],
        foreground=C["cyan2"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", C["panel2"])])

    style.configure(
        "Cyber.Horizontal.TProgressbar",
        troughcolor=C["black"],
        bordercolor=C["line"],
        background=C["cyan"],
        lightcolor=C["cyan"],
        darkcolor=C["cyan"],
    )


class MetricCard(ttk.Frame):
    def __init__(self, parent, title: str):
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.value_var = tk.StringVar(value="--")
        self.label_var = tk.StringVar(value=title)

        ttk.Label(self, textvariable=self.value_var, style="MetricValue.TLabel").pack(anchor="w")
        ttk.Label(self, textvariable=self.label_var, style="MetricLabel.TLabel").pack(anchor="w", pady=(4, 0))

    def set(self, value: str):
        self.value_var.set(value)


class DashboardTab(ttk.Frame):
    def __init__(self, parent, gs: GlobalState):
        super().__init__(parent, style="TFrame")
        self.gs = gs

        top = ttk.Frame(self, style="Panel.TFrame", padding=10)
        top.pack(fill="x", padx=10, pady=(10, 8))

        self.health_var = tk.StringVar(value="Overall Health: --")
        self.status_var = tk.StringVar(value="Status: CONNECTING")
        self.api_var = tk.StringVar(value=f"API: {self.gs.api_base()}")

        ttk.Label(top, textvariable=self.health_var, style="Panel.TLabel").pack(side="left")
        ttk.Label(top, text="•", style="Panel.TLabel").pack(side="left", padx=8)
        ttk.Label(top, textvariable=self.status_var, style="Panel.TLabel").pack(side="left")
        ttk.Label(top, text="•", style="Panel.TLabel").pack(side="left", padx=8)
        ttk.Label(top, textvariable=self.api_var, style="Panel.TLabel").pack(side="left")

        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(top, text="Restart DeepSentinel", command=self.restart_ml).pack(side="right", padx=6)
        ttk.Button(top, text="DeepSentinel Test", command=self.fail_ml).pack(side="right", padx=6)

        metrics = ttk.Frame(self, style="TFrame")
        metrics.pack(fill="x", padx=10, pady=(0, 8))

        self.metric_health = MetricCard(metrics, "PLATFORM HEALTH")
        self.metric_degraded = MetricCard(metrics, "DEGRADED ENGINES")
        self.metric_chains = MetricCard(metrics, "RESPONSE EVENTS")
        self.metric_tier = MetricCard(metrics, "MAX TIER")

        for i, card in enumerate((self.metric_health, self.metric_degraded, self.metric_chains, self.metric_tier)):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            metrics.columnconfigure(i, weight=1)

        health_panel = ttk.Frame(self, style="Panel.TFrame", padding=10)
        health_panel.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(health_panel, text="SYSTEM HEALTH", style="Section.TLabel").pack(anchor="w")
        self.health_progress = ttk.Progressbar(
            health_panel,
            style="Cyber.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.health_progress.pack(fill="x", pady=(10, 4))
        self.health_detail = tk.StringVar(value="Awaiting data")
        ttk.Label(health_panel, textvariable=self.health_detail, style="Panel.TLabel").pack(anchor="w")

        cols = ("engine", "state", "health", "service", "last_error")
        tree_panel = ttk.Frame(self, style="Panel.TFrame", padding=8)
        tree_panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ttk.Label(tree_panel, text="ENGINE GRID", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.tree = ttk.Treeview(tree_panel, columns=cols, show="headings", height=18)
        widths = {
            "engine": 180,
            "state": 100,
            "health": 80,
            "service": 180,
            "last_error": 540,
        }
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=widths[c], anchor="w")

        self.tree.tag_configure("nominal", foreground=C["green"])
        self.tree.tag_configure("degraded", foreground=C["gold"])
        self.tree.tag_configure("critical", foreground=C["red"])

        y = ttk.Scrollbar(tree_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")

    def fail_ml(self):
        try:
            api_post(self.gs.api_base(), "/engines/ml/fail", {
                "message": "DeepSentinel desktop test",
                "health": 25,
            })
            self.refresh()
        except Exception as e:
            messagebox.showerror("DeepSentinel Test Failed", str(e))

    def restart_ml(self):
        try:
            api_post(self.gs.api_base(), "/engines/ml/restart", {})
            self.refresh()
        except Exception as e:
            messagebox.showerror("Restart Failed", str(e))

    def refresh(self):
        try:
            self.api_var.set(f"API: {self.gs.api_base()}")

            ev_data = api_get(self.gs.api_base(), "/events")
            events = ev_data.get("events", [])
            if not isinstance(events, list):
                events = []

            try:
                data = api_get(self.gs.api_base(), "/engines")
                engines = data.get("engines", [])
                if not isinstance(engines, list):
                    engines = []
            except Exception:
                engines = derive_engines_from_events(events)

            for item in self.tree.get_children():
                self.tree.delete(item)

            total = 0.0
            count = 0
            degraded = 0
            max_tier = 0
            response_events = 0

            for ev in events:
                if str(ev.get("type", "")).startswith("response."):
                    response_events += 1
                    payload = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
                    try:
                        max_tier = max(max_tier, int(payload.get("tier", 0) or 0))
                    except Exception:
                        pass

            for eng in engines:
                name = str(eng.get("name", eng.get("id", "unknown")))
                state = str(eng.get("state", "unknown"))
                health = eng.get("health", "--")
                service = str(eng.get("service", ""))
                last_error = str(eng.get("last_error", ""))

                tag = "nominal"
                if state.lower() == "degraded":
                    tag = "degraded"
                if str(health).isdigit() and float(health) < 30:
                    tag = "critical"

                self.tree.insert("", "end", values=(name, state, health, service, last_error), tags=(tag,))

                try:
                    total += float(health)
                    count += 1
                except Exception:
                    pass

                if state.lower() == "degraded":
                    degraded += 1

            overall = round(total / count, 1) if count else 0.0
            self.health_var.set(f"Overall Health: {overall}%")
            self.health_progress["value"] = overall
            self.metric_health.set(f"{overall}%")
            self.metric_degraded.set(str(degraded))
            self.metric_chains.set(str(response_events))
            self.metric_tier.set(str(max_tier or 0))

            if degraded:
                self.status_var.set(f"Status: DEGRADED ({degraded})")
            else:
                self.status_var.set("Status: NOMINAL")

            self.health_detail.set(
                f"{count} engines tracked • {degraded} degraded • max containment tier {max_tier or 0}"
            )
        except Exception as e:
            self.status_var.set(f"Status: OFFLINE - {e}")


class EventsTab(ttk.Frame):
    def __init__(self, parent, gs: GlobalState):
        super().__init__(parent, style="TFrame")
        self.gs = gs

        top = ttk.Frame(self, style="Panel.TFrame", padding=10)
        top.pack(fill="x", padx=10, pady=(10, 8))

        self.info_var = tk.StringVar(value="Latest events")
        ttk.Label(top, textvariable=self.info_var, style="Panel.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")

        cols = ("time", "type", "level", "target", "message")
        panel = ttk.Frame(self, style="Panel.TFrame", padding=8)
        panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ttk.Label(panel, text="LIVE EVENT STREAM", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.tree = ttk.Treeview(panel, columns=cols, show="headings", height=24)
        widths = {
            "time": 170,
            "type": 240,
            "level": 90,
            "target": 160,
            "message": 620,
        }
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=widths[c], anchor="w")

        self.tree.tag_configure("info", foreground=C["cyan2"])
        self.tree.tag_configure("warning", foreground=C["gold"])
        self.tree.tag_configure("critical", foreground=C["red"])

        y = ttk.Scrollbar(panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")

    def refresh(self):
        try:
            data = api_get(self.gs.api_base(), "/events")
            events = data.get("events", [])
            if not isinstance(events, list):
                events = []

            for item in self.tree.get_children():
                self.tree.delete(item)

            shown = 0
            for ev in events[:180]:
                level = str(ev.get("level", "")).lower()
                tag = level if level in {"info", "warning", "critical"} else ""
                self.tree.insert("", "end", values=(
                    str(ev.get("ts", "")),
                    str(ev.get("type", "")),
                    str(ev.get("level", "")),
                    str(ev.get("target", "")),
                    str(ev.get("message", "")),
                ), tags=(tag,))
                shown += 1

            self.info_var.set(f"Latest events ({shown} shown)")
        except Exception as e:
            self.info_var.set(f"Events unavailable: {e}")


class ResponseTab(ttk.Frame):
    def __init__(self, parent, gs: GlobalState):
        super().__init__(parent, style="TFrame")
        self.gs = gs

        top = ttk.Frame(self, style="Panel.TFrame", padding=10)
        top.pack(fill="x", padx=10, pady=(10, 8))

        self.info_var = tk.StringVar(value="Containment chains")
        ttk.Label(top, textvariable=self.info_var, style="Panel.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")

        cols = ("time", "type", "tier", "action", "target", "message")
        panel = ttk.Frame(self, style="Panel.TFrame", padding=8)
        panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ttk.Label(panel, text="AUTONOMOUS RESPONSE CHAINS", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.tree = ttk.Treeview(panel, columns=cols, show="headings", height=24)
        widths = {
            "time": 170,
            "type": 250,
            "tier": 60,
            "action": 180,
            "target": 180,
            "message": 560,
        }
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=widths[c], anchor="w")

        self.tree.tag_configure("tier1", foreground=C["green"])
        self.tree.tag_configure("tier2", foreground=C["gold"])
        self.tree.tag_configure("tier3", foreground=C["red"])

        y = ttk.Scrollbar(panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")

    def refresh(self):
        try:
            data = api_get(self.gs.api_base(), "/events")
            events = data.get("events", [])
            if not isinstance(events, list):
                events = []

            for item in self.tree.get_children():
                self.tree.delete(item)

            shown = 0
            for ev in events:
                et = str(ev.get("type", ""))
                if not et.startswith("response."):
                    continue

                payload = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
                tier = str(payload.get("tier", ""))
                action = str(payload.get("action", ""))

                tag = ""
                if tier == "1":
                    tag = "tier1"
                elif tier == "2":
                    tag = "tier2"
                elif tier == "3":
                    tag = "tier3"

                self.tree.insert("", "end", values=(
                    str(ev.get("ts", "")),
                    et,
                    tier,
                    action,
                    str(ev.get("target", "")),
                    str(ev.get("message", "")),
                ), tags=(tag,))
                shown += 1
                if shown >= 180:
                    break

            self.info_var.set(f"Containment chains ({shown} shown)")
        except Exception as e:
            self.info_var.set(f"Response unavailable: {e}")


class TerminalTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="TFrame")
        self.proc_queue: queue.Queue[str] = queue.Queue()

        top = ttk.Frame(self, style="Panel.TFrame", padding=10)
        top.pack(fill="x", padx=10, pady=(10, 8))

        self.cmd_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.cmd_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _e: self.run_command())

        ttk.Button(top, text="Run", command=self.run_command).pack(side="left", padx=6)
        ttk.Button(top, text="Clear", command=self.clear_output).pack(side="left")

        shell = ttk.Frame(self, style="Panel.TFrame", padding=8)
        shell.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ttk.Label(shell, text="VEILCORE TERMINAL", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.output = tk.Text(
            shell,
            wrap="word",
            bg=C["black"],
            fg=C["cyan2"],
            insertbackground=C["cyan"],
            relief="flat",
            font=("Consolas", 10),
        )
        self.output.pack(fill="both", expand=True)
        self.after(150, self._drain_queue)

    def run_command(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        self.output.insert("end", f"$ {cmd}\n")
        self.output.see("end")

        def worker():
            try:
                proc = subprocess.run(
                    ["/bin/bash", "-lc", cmd],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if proc.stdout:
                    self.proc_queue.put(proc.stdout)
                if proc.stderr:
                    self.proc_queue.put(proc.stderr)
            except Exception as e:
                self.proc_queue.put(str(e) + "\n")

        threading.Thread(target=worker, daemon=True).start()

    def clear_output(self):
        self.output.delete("1.0", "end")

    def _drain_queue(self):
        while not self.proc_queue.empty():
            self.output.insert("end", self.proc_queue.get())
            self.output.see("end")
        self.after(150, self._drain_queue)


class VeilCoreDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.gs = GlobalState()

        apply_theme(self)

        self.title(APP_TITLE)
        self.geometry("1450x920+120+80")
        self.minsize(1100, 700)

        header = ttk.Frame(self, style="Panel.TFrame", padding=12)
        header.pack(fill="x", padx=10, pady=(10, 8))

        left = ttk.Frame(header, style="Panel.TFrame")
        left.pack(side="left", fill="x", expand=True)

        self.brand_var = tk.StringVar(value="VEILCORE :: WHITE NODE")
        self.status_var = tk.StringVar(value="CONNECTING")
        self.sub_var = tk.StringVar(value="Cyber Defense Platform")

        ttk.Label(left, textvariable=self.brand_var, style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, textvariable=self.sub_var, style="Panel.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(left, textvariable=self.status_var, style="Panel.TLabel").pack(anchor="w", pady=(6, 0))

        right = ttk.Frame(header, style="Panel.TFrame")
        right.pack(side="right")

        self.api_var = tk.StringVar(value=self.gs.api_base())
        ttk.Label(right, text="VEIL_API", style="Panel.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.api_entry = ttk.Entry(right, textvariable=self.api_var, width=30)
        self.api_entry.grid(row=0, column=1, padx=(0, 6))
        ttk.Button(right, text="Apply", command=self.apply_settings).grid(row=0, column=2)

        self.notebook = ttk.Notebook(self)
        self.dashboard = DashboardTab(self.notebook, self.gs)
        self.events = EventsTab(self.notebook, self.gs)
        self.response = ResponseTab(self.notebook, self.gs)
        self.terminal = TerminalTab(self.notebook)

        self.notebook.add(self.dashboard, text="Overview")
        self.notebook.add(self.events, text="Events")
        self.notebook.add(self.response, text="Response Chains")
        self.notebook.add(self.terminal, text="Terminal")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.after(400, self.refresh_all)

    def apply_settings(self):
        self.gs.api_base_url = self.api_var.get().strip() or DEFAULT_API
        self.refresh_all()

    def refresh_all(self):
        try:
            self.dashboard.refresh()
            self.events.refresh()
            self.response.refresh()
            status_text = self.dashboard.status_var.get()
            self.status_var.set(status_text.replace("Status: ", ""))
        except Exception as e:
            self.status_var.set(f"OFFLINE - {e}")
        self.after(2500, self.refresh_all)


def main():
    app = VeilCoreDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
