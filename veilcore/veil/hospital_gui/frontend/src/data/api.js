// src/data/api.js
export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

// Always same-origin. Always include cookies. Never store tokens.
export async function apiFetch(path, options = {}) {
  const opts = {
    method: options.method || "GET",
    headers: {
      "Accept": "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    credentials: "include",
    cache: "no-store",
    ...options,
  };

  if (options.body && typeof options.body !== "string") {
    opts.body = JSON.stringify(options.body);
  }

  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new ApiError("Network error. Please check connectivity.", 0, null);
  }

  if (res.status === 401) {
    window.location.href = "/login";
    throw new ApiError("Unauthorized", 401, null);
  }

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  let payload = null;
  if (isJson) {
    try { payload = await res.json(); } catch { payload = null; }
  } else {
    try { await res.text(); } catch {}
  }

  if (!res.ok) {
    const msg =
      (payload && (payload.detail || payload.message)) ||
      (res.status >= 500
        ? "Server error. Please try again."
        : "Request failed. Please check your input.");
    throw new ApiError(msg, res.status, payload);
  }

  return payload;
}
