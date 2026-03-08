from __future__ import annotations

import threading
import time
import traceback
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox


# ---------- Orchestrator API (tolerant wrapper) ----------

def _to_dict(x: Any) -> Dict[str, Any]:
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    if is_dataclass(x):
        return asdict(x)
    d = getattr(x, "__dict__", None)
    if isinstance(d, dict):
        return dict(d)
    # last resort: attributes
    out: Dict[str, Any] = {}
    for k in ("name", "running", "pid", "log", "tier", "status"):
        if hasattr(x, k):
            out[k] = getattr(x, k)
    return out


def _import_orchestrator():
    """
    Supports multiple internal APIs:
      - list_services()/start_service()/stop_service()/status()
      - list()/start()/stop()/status()
      - ServiceStatus objects returned
    """
    import veil.orchestrator as orch  # type: ignore
    return orch


def orch_list_services() -> List[Dict[str, Any]]:
    orch = _import_orchestrator()
    fn = getattr(orch, "list_services", None) or getattr(orch, "list", None)
    if not callable(fn):
        raise RuntimeError("orchestrator: missing list_services/list")
    items = fn()
    return [_to_dict(s) for s in (items or [])]


def orch_status(name: str) -> Dict[str, Any]:
    orch = _import_orchestrator()
    fn = getattr(orch, "status", None) or getattr(orch, "service_status", None)
    if not callable(fn):
        # Some builds only expose `status(name)`; `service_status` may not exist.
        raise RuntimeError("orchestrator: missing status()")
    return _to_dict(fn(name))


def orch_start(name: str, dry_run: bool) -> Dict[str, Any]:
    orch = _import_orchestrator()
    fn = getattr(orch, "start_service", None) or getattr(orch, "start", None)
    if not callable(fn):
        raise RuntimeError("orchestrator: missing start_service/start")
    # tolerate different signatures
    try:
        res = fn(name, dry_run=dry_run)
    except TypeError:
        res = fn(name)
    return _to_dict(res)


def orch_stop(name: str, dry_run: bool) -> Dict[str, Any]:
    orch = _import_orchestrator()
    fn = getattr(orch, "stop_service", None) or getattr(orch, "stop", None)
    if not callable(fn):
        raise RuntimeError("orchestrator: missing stop_service/stop")
    try:
        res = fn(name, dry_run=dry_run)
    except TypeError:
        res = fn(name)
    return _to_dict(res)


# ---------- GUI ----------

class VeilHospitalGUIOrgans(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Veil Security & Hardening Tracker — Organs")
        self.geometry("1100x700")
        self.minsize(950, 620)

        self._dry_run = tk.BooleanVar(value=True)

        # action runner state
        self._action_lock = threading.Lock()
        self._action_thread: Optional[threading.Thread] = None
        self._cancel_flag = threading.Event()

        self._build_ui()
        self._refresh_services()
        self.after(1500, self._poll_refresh)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        # Top bar
        top = ttk.Frame(root)
        top.pack(fill="x")

        ttk.Label(top, text="Veil Orchestrator", font=("Segoe UI", 14, "bold")).pack(side="left")

        ttk.Checkbutton(top, text="Dry-run", variable=self._dry_run).pack(side="right")
        ttk.Button(top, text="Refresh", command=self._refresh_services).pack(side="right", padx=(0, 8))

        # Main split
        paned = ttk.Panedwindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(10, 0))

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        # Services table
        cols = ("name", "running", "pid", "log")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        self.tree.heading("name", text="Service")
        self.tree.heading("running", text="Status")
        self.tree.heading("pid", text="PID")
        self.tree.heading("log", text="Log")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("running", width=90, anchor="center")
        self.tree.column("pid", width=90, anchor="center")
        self.tree.column("log", width=520, anchor="w")

        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._render_selected_details())
        self.tree.bind("<Double-1>", lambda e: self._toggle_selected())

        # Buttons row
        btns = ttk.Frame(left)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        btns.columnconfigure(0, weight=1)

        self.btn_play = ttk.Button(btns, text="▶ Play", command=self._start_selected)
        self.btn_stop = ttk.Button(btns, text="■ Stop", command=self._stop_selected)
        self.btn_cancel = ttk.Button(btns, text="✖ Cancel", command=self._cancel_action)

        self.btn_play.pack(side="left")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_cancel.pack(side="left", padx=(8, 0))

        ttk.Label(btns, text="Tip: Double-click a row to start/stop").pack(side="right")

        # Right side: details + terminal
        details = ttk.LabelFrame(right, text="Service Details", padding=10)
        details.pack(fill="x")

        self.detail_text = tk.Text(details, height=8, wrap="none")
        self.detail_text.configure(state="disabled")
        self.detail_text.pack(fill="x")

        terminal = ttk.LabelFrame(right, text="Terminal", padding=10)
        terminal.pack(fill="both", expand=True, pady=(10, 0))

        self.term = tk.Text(terminal, wrap="word")
        self.term.configure(font=("Consolas", 10))
        self.term.pack(fill="both", expand=True)

        self._log("GUI ready. Dry-run is ON by default.\n")

    def _log(self, msg: str) -> None:
        self.term.insert("end", msg)
        self.term.see("end")

    def _selected_name(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        vals = self.tree.item(iid, "values")
        if not vals:
            return None
        return str(vals[0])

    def _render_selected_details(self) -> None:
        name = self._selected_name()
        if not name:
            return
        try:
            s = orch_status(name)
        except Exception as e:
            s = {"name": name, "error": str(e)}

        running = s.get("running", False)
        pid = s.get("pid", None)
        logp = s.get("log", "")
        tier = s.get("tier", "—")

        text = (
            f"Name:     {name}\n"
            f"Status:   {'● RUNNING' if running else '○ STOPPED'}\n"
            f"PID:      {pid}\n"
            f"Tier:     {tier}\n"
            f"Log Path: {logp}\n"
        )

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_play.configure(state=state)
        self.btn_stop.configure(state=state)
        self.btn_cancel.configure(state="normal" if busy else "disabled")

    def _run_action(self, title: str, fn) -> None:
        with self._action_lock:
            if self._action_thread and self._action_thread.is_alive():
                self._log("Busy: an action is already running.\n")
                return
            self._cancel_flag.clear()
            self._set_busy(True)

            def worker():
                try:
                    self._log(f"\n=== {title} ===\n")
                    if self._cancel_flag.is_set():
                        self._log("Canceled before start.\n")
                        return
                    res = fn()
                    if self._cancel_flag.is_set():
                        self._log("Canceled.\n")
                        return
                    self._log(f"OK: {res}\n")
                except Exception:
                    self._log("ERROR:\n" + traceback.format_exc() + "\n")
                finally:
                    self.after(0, lambda: self._set_busy(False))
                    self.after(0, self._refresh_services)

            self._action_thread = threading.Thread(target=worker, daemon=True)
            self._action_thread.start()

    def _cancel_action(self) -> None:
        self._cancel_flag.set()
        self._log("Cancel requested.\n")

    def _start_selected(self) -> None:
        name = self._selected_name()
        if not name:
            messagebox.showinfo("Veil", "Select a service first.")
            return
        dry = bool(self._dry_run.get())
        self._run_action(
            f"veil orchestrator start {name} ({'dry-run' if dry else 'apply'})",
            lambda: orch_start(name, dry_run=dry),
        )

    def _stop_selected(self) -> None:
        name = self._selected_name()
        if not name:
            messagebox.showinfo("Veil", "Select a service first.")
            return
        dry = bool(self._dry_run.get())
        self._run_action(
            f"veil orchestrator stop {name} ({'dry-run' if dry else 'apply'})",
            lambda: orch_stop(name, dry_run=dry),
        )

    def _toggle_selected(self) -> None:
        name = self._selected_name()
        if not name:
            return
        try:
            s = orch_status(name)
            if bool(s.get("running")):
                self._stop_selected()
            else:
                self._start_selected()
        except Exception as e:
            messagebox.showerror("Veil", f"Could not toggle {name}:\n{e}")

    def _refresh_services(self) -> None:
        try:
            services = orch_list_services()
        except Exception as e:
            self._log("ERROR listing services:\n" + str(e) + "\n")
            services = []

        # Preserve selection name
        selected = self._selected_name()

        self.tree.delete(*self.tree.get_children())
        for s in services:
            name = str(s.get("name", ""))
            running = bool(s.get("running", False))
            pid = s.get("pid", None)
            logp = str(s.get("log", ""))
            status = "RUNNING" if running else "STOPPED"
            iid = self.tree.insert("", "end", values=(name, status, pid, logp))
            if selected and name == selected:
                self.tree.selection_set(iid)

        self._render_selected_details()

    def _poll_refresh(self) -> None:
        # periodic refresh (no spam)
        self._refresh_services()
        self.after(2000, self._poll_refresh)


def main() -> int:
    app = VeilHospitalGUIOrgans()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
