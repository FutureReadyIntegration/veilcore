(() => {
  "use strict";

  // ---------------------------------------------------------------------------
  // Window Manager — DOM Executor
  // Owns rendering, z-order, drag, and visual focus.
  // Does NOT decide policy.
  // ---------------------------------------------------------------------------

  let zTop = 10;

  // Public entrypoint called by desktop.js
  window.wmCreateWindow = function wmCreateWindow(record) {
    if (!record || !record.id || !record.root) {
      console.error("wm.js: invalid window record");
      return;
    }

    const desktop = document.getElementById("desktop");
    if (!desktop) {
      console.error("wm.js: missing #desktop");
      return;
    }

    // Window shell
    const w = document.createElement("div");
    w.className = "window";
    w.dataset.windowId = record.id;
    w.style.left = "80px";
    w.style.top = "80px";
    w.style.zIndex = String(++zTop);

    // Title bar
    const bar = document.createElement("div");
    bar.className = "titlebar";
    bar.textContent = record.title || record.id;

    // Content
    const body = document.createElement("div");
    body.className = "body";
    body.appendChild(record.root);

    w.appendChild(bar);
    w.appendChild(body);
    desktop.appendChild(w);

    enableFocus(w);
    enableDrag(w, bar);
  };

  // ---------------------------------------------------------------------------
  // Visual Focus (z-order only)
  // ---------------------------------------------------------------------------

  function enableFocus(w) {
    w.addEventListener("mousedown", () => {
      w.style.zIndex = String(++zTop);
    });
  }

  // ---------------------------------------------------------------------------
  // Dragging (visual only)
  // ---------------------------------------------------------------------------

  function enableDrag(w, bar) {
    let dragging = false;
    let sx = 0, sy = 0, ox = 0, oy = 0;

    bar.addEventListener("mousedown", (e) => {
      dragging = true;
      sx = e.clientX;
      sy = e.clientY;
      const r = w.getBoundingClientRect();
      ox = r.left;
      oy = r.top;
      e.preventDefault();
    });

    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      w.style.left = (ox + e.clientX - sx) + "px";
      w.style.top  = (oy + e.clientY - sy) + "px";
    });

    window.addEventListener("mouseup", () => {
      dragging = false;
    });
  }

})();
