from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix
from collections import Counter

stats_bp = Blueprint("sidebar_stats", __name__)

@stats_bp.route("/glyph-stats")
def glyph_stats():
    matrix = render_glyph_matrix()
    role_counts = Counter(e["role"] for e in matrix)
    tier_counts = Counter(e["tier"] for e in matrix)

    stats = {
        "total": len(matrix),
        "roles": role_counts,
        "tiers": tier_counts,
        "critical_pct": round(100 * tier_counts.get("critical", 0) / max(len(matrix), 1), 2)
    }
    return render_template("sidebar_stats.html", stats=stats)
