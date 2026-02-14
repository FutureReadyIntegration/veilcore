export function createWindow(title, content, meta = "") {
  const win = document.createElement("div");
  win.className = "window";

  const safeTitle = escapeHtml(String(title ?? "Untitled"));
  const safeMeta = escapeHtml(String(meta ?? ""));

  win.innerHTML = `
    <div class="titlebar">
      <div class="title">${safeTitle}</div>
      <div class="meta">${safeMeta}</div>
    </div>
    <pre>${escapeHtml(String(content ?? ""))}</pre>
  `;

  document.getElementById("desktop").appendChild(win);
  return win;
}

export function clearDesktop() {
  const d = document.getElementById("desktop");
  d.innerHTML = "";
}

function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
