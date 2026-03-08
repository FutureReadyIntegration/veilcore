async function fetchOrgans() {
  const res = await fetch('/api/organs');
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return await res.json();
}

function pillFor(systemd) {
  const active = systemd?.active || 'unknown';
  const sub = systemd?.sub || 'unknown';
  const ok = (active === 'active' && (sub === 'running' || sub === 'listening'));
  const cls = ok ? 'pill ok' : 'pill bad';
  return `<span class="${cls}">${active}/${sub}</span>`;
}

function render(data) {
  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const organs = (data && data.organs) ? data.organs : [];
  for (const o of organs) {
    const unit = o.systemd_unit || '—';
    const pid = o.systemd?.pid || '0';
    const desc = o.description || '';
    const glyph = o.glyph || '✶';
    const arche = o.archetype || 'organ';
    const status = pillFor(o.systemd);

    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="top">
        <div>
          <div class="name">${glyph} ${o.name} <span class="dim small">(${o.id})</span></div>
          <div class="small dim">${arche}</div>
        </div>
        <div>${status}</div>
      </div>
      <div class="desc">${desc}</div>
      <div class="small dim" style="margin-top:10px;">
        unit: <code>${unit}</code> · pid: <code>${pid}</code>
      </div>
    `;
    grid.appendChild(card);
  }

  document.getElementById('lastUpdated').textContent =
    `updated: ${new Date().toLocaleString()}`;
}

function showError(err) {
  const el = document.getElementById('error');
  el.style.display = 'block';
  el.textContent = String(err?.stack || err);
}

async function refresh() {
  document.getElementById('error').style.display = 'none';
  const data = await fetchOrgans();
  render(data);
}

document.getElementById('refreshBtn').addEventListener('click', () => refresh().catch(showError));
refresh().catch(showError);
setInterval(() => refresh().catch(() => {}), 5000);
