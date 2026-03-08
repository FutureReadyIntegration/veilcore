// service_veil.js
// Veil Service UI — window request only
// No authority. No rendering decisions.

(function () {
  "use strict";

  function bootVeilService() {
    const root = document.createElement("div");
    root.id = "veil-service-root";
    root.textContent = "Veil Service Online";

    const record = {
      id: "veil-service",
      title: "Veil Service",
      root: root
    };

    // Explicit request — no fallback, no inference
    if (typeof window.createWindow !== "function") {
      console.error("service_veil.js: createWindow not available");
      return;
    }

    window.createWindow(record);
  }

  // Explicit boot — no auto‑discovery
  document.addEventListener("DOMContentLoaded", bootVeilService);

})();
