from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime
from pathlib import Path
import psutil
import subprocess
import time
import os
import json

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

START_TIME = time.time()
PID = os.getpid()


# ---------------------------------------------------------------------------
# Helpers: systemd + metrics
# ---------------------------------------------------------------------------

def _run_cmd(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _get_service_main_pid(unit: str) -> int:
    # unit like "veil-insider-threat.service"
    out = _run_cmd(["systemctl", "show", unit, "-p", "MainPID", "--value"])
    out = out.strip()
    try:
        pid = int(out)
        return pid if pid > 0 else 0
    except Exception:
        return 0


def _get_veil_services():
    """
    Discover all veil-* services via systemd and attach basic state + metrics.
    """
    out = _run_cmd(
        ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"]
    )
    services = []
    now = time.time()

    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        unit = parts[0]  # e.g. veil-dashboard.service
        if not unit.startswith("veil-") or not unit.endswith(".service"):
            continue

        load = parts[1] if len(parts) > 1 else "unknown"
        active = parts[2] if len(parts) > 2 else "unknown"
        sub = parts[3] if len(parts) > 3 else "unknown"
        description = " ".join(parts[4:]) if len(parts) > 4 else unit

        pid = _get_service_main_pid(unit)
        cpu_percent = None
        mem_mb = None
        uptime_seconds = None

        if pid > 0:
            try:
                p = psutil.Process(pid)
                # psutil cpu_percent needs a small interval for a fresh sample
                cpu_percent = p.cpu_percent(interval=0.05)
                mem_mb = p.memory_info().rss / (1024 * 1024)
                create_time = p.create_time()
                uptime_seconds = int(now - create_time)
            except Exception:
                pass

        # status classification
        if active == "active" and sub == "running":
            status = "running"
        elif active in ("activating", "reloading") or "auto-restart" in description.lower():
            status = "degraded"
        elif active in ("failed", "inactive"):
            status = "failed"
        else:
            status = "unknown"

        # color mapping
        if status == "running":
            color = "#1f8b4c"  # green
        elif status == "degraded":
            color = "#c9a227"  # yellow
        elif status == "failed":
            color = "#b33939"  # red
        else:
            color = "#555b6e"  # gray

        organ_id = unit.removeprefix("veil-").removesuffix(".service")

        services.append(
            {
                "unit": unit,
                "id": organ_id,
                "name": organ_id.replace("-", " ").title(),
                "description": description,
                "load": load,
                "active": active,
                "sub": sub,
                "status": status,
                "color": color,
                "pid": pid,
                "cpu_percent": cpu_percent,
                "memory_mb": mem_mb,
                "uptime_seconds": uptime_seconds,
            }
        )

    return services


def _format_uptime(seconds: int | None) -> str:
    if not seconds or seconds <= 0:
        return "—"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
def dashboard_status():
    uptime_seconds = time.time() - START_TIME
    return {
        "organ": "veil-dashboard",
        "status": "online",
        "uptime_seconds": int(uptime_seconds),
        "uptime_human": f"{uptime_seconds/3600:.2f} hours",
        "pid": PID,
        "threads": psutil.Process(PID).num_threads(),
        "cpu_percent": psutil.cpu_percent(interval=0.05),
        "memory_mb": psutil.Process(PID).memory_info().rss / (1024 * 1024),
        "last_restart": datetime.fromtimestamp(START_TIME).isoformat(),
    }


@router.get("/events")
def dashboard_events():
    return {
        "events": [
            {"type": "heartbeat", "message": "Dashboard organ online"},
            {"type": "system", "message": "System stable"},
            {"type": "info", "message": "Veil OS cockpit ready"},
        ]
    }


@router.get("/organs")
def list_organs():
    return {"organs": _get_veil_services()}


@router.get("/organs/{organ_id}")
def organ_detail(organ_id: str):
    organs = _get_veil_services()
    for o in organs:
        if o["id"] == organ_id:
            # Optionally, look for a status.json in a conventional path
            status_file = Path(f"/var/lib/veil/{organ_id}/status.json")
            extra_status = None
            if status_file.exists():
                try:
                    extra_status = json.loads(status_file.read_text())
                except Exception:
                    extra_status = None
            return {"organ": o, "extra_status": extra_status}
    return {"error": "organ_not_found", "organ_id": organ_id}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@router.get("/ui", response_class=HTMLResponse)
def dashboard_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Veil OS — Cockpit</title>
        <style>
            body {
                background-color: #050608;
                color: #e0e0e0;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                margin: 0;
            }
            header {
                padding: 20px 30px;
                border-bottom: 1px solid #222;
                color: #6ab0ff;
                font-size: 22px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            header .subtitle {
                font-size: 12px;
                color: #888;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .layout {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                padding: 20px 30px 30px 30px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 16px;
            }
            .card {
                background: #101218;
                padding: 16px;
                border-radius: 10px;
                border: 1px solid #262a33;
                cursor: pointer;
                transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, border-color 0.08s ease-out;
            }
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.5);
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                margin-bottom: 6px;
            }
            .card-title {
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #8fbaff;
            }
            .card-status {
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .status-running {
                color: #4cd964;
            }
            .status-degraded {
                color: #ffd86b;
            }
            .status-failed {
                color: #ff6b6b;
            }
            .status-unknown {
                color: #999;
            }
            .card-body {
                margin-top: 8px;
                font-size: 13px;
                color: #c0c0c0;
            }
            .metric-row {
                display: flex;
                justify-content: space-between;
                margin-top: 4px;
            }
            .metric-label {
                color: #777;
            }
            .metric-value {
                font-weight: 500;
            }
            .events, .detail {
                background: #101218;
                padding: 16px;
                border-radius: 10px;
                border: 1px solid #262a33;
            }
            .events-title, .detail-title {
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #8fbaff;
                margin-bottom: 8px;
            }
            .event-item {
                padding: 6px 0;
                border-bottom: 1px solid #262a33;
                font-size: 13px;
            }
            .event-item:last-child {
                border-bottom: none;
            }
            .detail-name {
                font-size: 16px;
                margin-bottom: 4px;
            }
            .detail-status {
                font-size: 13px;
                margin-bottom: 8px;
            }
            .detail-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 6px 16px;
                font-size: 13px;
            }
            .detail-label {
                color: #777;
            }
            .detail-value {
                color: #ddd;
            }
            .pill {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .pill-running {
                background: rgba(79, 209, 146, 0.12);
                color: #4cd964;
            }
            .pill-degraded {
                background: rgba(255, 216, 107, 0.12);
                color: #ffd86b;
            }
            .pill-failed {
                background: rgba(255, 107, 107, 0.12);
                color: #ff6b6b;
            }
            .pill-unknown {
                background: rgba(153, 153, 153, 0.12);
                color: #aaa;
            }
            .muted {
                color: #777;
            }
            .small {
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <header>
            <div>
                Veil OS — Cockpit
                <div class="subtitle">Multi-organ operator surface</div>
            </div>
            <div class="small muted" id="summary"></div>
        </header>

        <div class="layout">
            <div>
                <div class="grid" id="organs-grid"></div>
            </div>
            <div>
                <div class="detail" id="detail-panel">
                    <div class="detail-title">Organ Detail</div>
                    <div class="muted small">Select an organ tile to view details.</div>
                </div>
                <div style="height: 16px;"></div>
                <div class="events">
                    <div class="events-title">Live Events</div>
                    <div id="events"></div>
                </div>
            </div>
        </div>

        <script>
            let selectedOrganId = null;

            function statusClass(status) {
                if (status === "running") return "status-running";
                if (status === "degraded") return "status-degraded";
                if (status === "failed") return "status-failed";
                return "status-unknown";
            }

            function pillClass(status) {
                if (status === "running") return "pill pill-running";
                if (status === "degraded") return "pill pill-degraded";
                if (status === "failed") return "pill pill-failed";
                return "pill pill-unknown";
            }

            function formatNumber(value, digits = 1) {
                if (value === null || value === undefined) return "—";
                return Number(value).toFixed(digits);
            }

            function formatUptime(seconds) {
                if (!seconds || seconds <= 0) return "—";
                const h = Math.floor(seconds / 3600);
                const m = Math.floor((seconds % 3600) / 60);
                if (h > 0) return `${h}h ${m}m`;
                return `${m}m`;
            }

            async function refreshOrgans() {
                try {
                    const res = await fetch('/dashboard/organs');
                    const data = await res.json();
                    const organs = data.organs || [];
                    const grid = document.getElementById('organs-grid');
                    grid.innerHTML = '';

                    let running = 0, degraded = 0, failed = 0;

                    organs.forEach(o => {
                        if (o.status === "running") running++;
                        else if (o.status === "degraded") degraded++;
                        else if (o.status === "failed") failed++;

                        const card = document.createElement('div');
                        card.className = 'card';
                        card.style.borderColor = o.color || '#262a33';
                        card.onclick = () => {
                            selectedOrganId = o.id;
                            refreshOrganDetail();
                        };

                        const header = document.createElement('div');
                        header.className = 'card-header';

                        const title = document.createElement('div');
                        title.className = 'card-title';
                        title.innerText = o.name || o.id;

                        const status = document.createElement('div');
                        status.className = 'card-status ' + statusClass(o.status);
                        status.innerText = (o.status || 'unknown').toUpperCase();

                        header.appendChild(title);
                        header.appendChild(status);

                        const body = document.createElement('div');
                        body.className = 'card-body';

                        const row1 = document.createElement('div');
                        row1.className = 'metric-row';
                        row1.innerHTML = `
                            <span class="metric-label">CPU</span>
                            <span class="metric-value">${formatNumber(o.cpu_percent)}%</span>
                        `;

                        const row2 = document.createElement('div');
                        row2.className = 'metric-row';
                        row2.innerHTML = `
                            <span class="metric-label">Memory</span>
                            <span class="metric-value">${formatNumber(o.memory_mb)} MB</span>
                        `;

                        const row3 = document.createElement('div');
                        row3.className = 'metric-row';
                        row3.innerHTML = `
                            <span class="metric-label">Uptime</span>
                            <span class="metric-value">${formatUptime(o.uptime_seconds)}</span>
                        `;

                        body.appendChild(row1);
                        body.appendChild(row2);
                        body.appendChild(row3);

                        card.appendChild(header);
                        card.appendChild(body);
                        grid.appendChild(card);
                    });

                    const summary = document.getElementById('summary');
                    summary.innerText = `Organs: ${organs.length} • Running: ${running} • Degraded: ${degraded} • Failed: ${failed}`;
                } catch (e) {
                    console.error('Failed to refresh organs', e);
                }
            }

            async function refreshOrganDetail() {
                const panel = document.getElementById('detail-panel');
                if (!selectedOrganId) {
                    panel.innerHTML = `
                        <div class="detail-title">Organ Detail</div>
                        <div class="muted small">Select an organ tile to view details.</div>
                    `;
                    return;
                }

                try {
                    const res = await fetch('/dashboard/organs/' + encodeURIComponent(selectedOrganId));
                    const data = await res.json();
                    if (data.error) {
                        panel.innerHTML = `
                            <div class="detail-title">Organ Detail</div>
                            <div class="muted small">Organ not found: ${selectedOrganId}</div>
                        `;
                        return;
                    }

                    const o = data.organ;
                    const extra = data.extra_status;

                    panel.innerHTML = `
                        <div class="detail-title">Organ Detail</div>
                        <div class="detail-name">${o.name || o.id}</div>
                        <div class="detail-status">
                            <span class="${pillClass(o.status)}">${(o.status || 'unknown').toUpperCase()}</span>
                            <span class="muted small" style="margin-left:8px;">${o.unit}</span>
                        </div>
                        <div class="detail-grid">
                            <div class="detail-label">Description</div>
                            <div class="detail-value">${o.description || '—'}</div>

                            <div class="detail-label">Load</div>
                            <div class="detail-value">${o.load}</div>

                            <div class="detail-label">Active</div>
                            <div class="detail-value">${o.active} / ${o.sub}</div>

                            <div class="detail-label">PID</div>
                            <div class="detail-value">${o.pid || '—'}</div>

                            <div class="detail-label">CPU</div>
                            <div class="detail-value">${formatNumber(o.cpu_percent)}%</div>

                            <div class="detail-label">Memory</div>
                            <div class="detail-value">${formatNumber(o.memory_mb)} MB</div>

                            <div class="detail-label">Uptime</div>
                            <div class="detail-value">${formatUptime(o.uptime_seconds)}</div>
                        </div>
                        ${
                            extra
                                ? `<div style="margin-top:10px;">
                                       <div class="detail-label">Extra Status</div>
                                       <pre class="detail-value small" style="background:#050608;padding:8px;border-radius:6px;overflow:auto;max-height:200px;">${JSON.stringify(extra, null, 2)}</pre>
                                   </div>`
                                : ''
                        }
                    `;
                } catch (e) {
                    console.error('Failed to refresh organ detail', e);
                    panel.innerHTML = `
                        <div class="detail-title">Organ Detail</div>
                        <div class="muted small">Error loading details for ${selectedOrganId}.</div>
                    `;
                }
            }

            async function refreshEvents() {
                try {
                    const res = await fetch('/dashboard/events');
                    const data = await res.json();
                    const container = document.getElementById('events');
                    container.innerHTML = '';
                    (data.events || []).forEach(ev => {
                        const div = document.createElement('div');
                        div.className = 'event-item';
                        div.innerText = `[${ev.type}] ${ev.message}`;
                        container.appendChild(div);
                    });
                } catch (e) {
                    console.error('Failed to refresh events', e);
                }
            }

            refreshOrgans();
            refreshEvents();
            setInterval(refreshOrgans, 2000);
            setInterval(refreshEvents, 3000);
            setInterval(refreshOrganDetail, 2500);
        </script>
    </body>
    </html>
    """
