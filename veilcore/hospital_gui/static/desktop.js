// desktop.js
// Desktop Policy Layer — explicit authority bridge
// No inference. No automation. No UI rendering.

(function () {
  "use strict";

  // Explicitly declared global entrypoint.
  // Services may request windows ONLY through this function.
  window.createWindow = function (record) {
    // Hard validation — fail fast, fail loud.
    if (!record || typeof record !== "object") {
      console.error("desktop.js: createWindow called with invalid record");
      return;
    }

    if (!record.id || !record.root) {
      console.error("desktop.js: window record missing required fields", record);
      return;
    }

    // Window Manager must already be present.
    if (typeof window.wmCreateWindow !== "function") {
      console.error("desktop.js: Window Manager not available");
      return;
    }

    // Forward request — no mutation, no interpretation.
    window.wmCreateWindow(record);
  };

})();
