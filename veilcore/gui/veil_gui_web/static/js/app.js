const grid = document.getElementById("organsGrid");
const statusPill = document.getElementById("statusPill");
const refreshBtn = document.getElementById("refreshBtn");

function badgeClass(active, sub) {
  if (active === "active" && (sub === "running" || sub === "listening")) return "ok";
  if (active === "activating" || sub?.includes("restart")) return "warn";
  if (active === "failed") return "bad";
  return "warn";
}

function render(organs) {
  grid.innerHTML = "";
  for (const o of organs) {
    const sys = o.systemd || {};
    const active = sys.active || "unknown";
    const sub = sys.sub || "";
    const cls = badgeClass(active, sub);

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="cardTop">
        <div class="cardTitle">
          <div class="cardGlyph">${o.glyph || "✶"}</div>
          <div>
            <div class="cardName">${o.name}</div>
            <div class="cardId">${o.id} · <code>${o.systemd_unit || ""}</code></div>
          </div>
        </div>
        <div class="badge ${cls}">${active}${sub ? " / " + sub : ""}</div>
      </div>

      <div class="meta">
        <div>PID: <code>${sys.pid || "0"}</code></div>
        <div>Description: <code>${sys.description || o.description || ""}</code></div>
      </div>
    `;
    grid.appendChild(card);
  }
}

async function refresh() {
  statusPill.textContent = "loading…";
  try {
    const res = await fetch("/api/organs", { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));
    render(data.organs || []);
    statusPill.textContent = `ok · ${data.organs?.length || 0} organs`;
  } catch (e) {
    statusPill.textContent = "error";
    grid.innerHTML = `<div class="card"><b>Failed to load organs</b><pre style="white-space:pre-wrap;color:#ff6b6b">${String(e)}</pre></div>`;
  }
}

refreshBtn.addEventListener("click", refresh);
refresh();
setInterval(refresh, 3000);

