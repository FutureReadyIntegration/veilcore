import os, json
from datetime import datetime

TIER_COLORS = {
    "critical":     "#ff4b4b",
    "guard":        "#ff884b",
    "immutable":    "#ffd24b",
    "experimental": "#8ad9ff",
    "general":      "#777777"
}

ROLE_ICONS = {
    "audit":    "⚖️",
    "sentry":   "👁",
    "ledger":   "📜",
    "r&d":      "🧪",
    "neutral":  "🔹"
}

def render_glyph_matrix(timeline_path="cathedral_codex/codex_timeline.json"):
    if not os.path.exists(timeline_path): return []
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    matrix = []
    for event in timeline:
        for m in event.get("matches", []):
            matrix.append({
                "timestamp": event["timestamp"],
                "glyph":     m["glyph"],
                "text":      m["text"],
                "file":      m["file"],
                "line":      m["line"],
                "role":      m["role"],
                "tier":      m["tier"],
                "level":     m["level"],
                "color":     TIER_COLORS.get(m["tier"], "#999"),
                "icon":      ROLE_ICONS.get(m["role"], "🔹")
            })
    return matrix

def export_matrix(path="cathedral_codex/glyph_matrix.json"):
    matrix = render_glyph_matrix()
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "entries": matrix
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    return snapshot
