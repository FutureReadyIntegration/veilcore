from flask import Flask, request, jsonify, render_template
from daemons.bittydaemon3 import (
    scan, cached_scan, get_cache_stats,
    get_disk_stats, auto_prune, export_snapshot,
    get_status
)
import json, os

app = Flask(__name__)

# 🩺 Status & Overview
@app.route("/bitty/status")
@app.route("/codex/overview")
def bitty_status():
    return render_template("bitty_status.html", status=get_status())

# 🔍 JSON Search
@app.route("/bitty/search")
def bitty_search():
    query = request.args.get("q", "")
    results = cached_scan(query)
    return jsonify({"query": query, "count": len(results), "results": results})

# 📖 HTML Search View
@app.route("/bitty/view")
def bitty_view():
    query = request.args.get("q", "")
    results = scan(query)
    return render_template("bitty_results.html", query=query, results=results)

# 📊 Cache Stats
@app.route("/bitty/stats")
def bitty_stats():
    return render_template("bitty_stats.html", stats=get_cache_stats())

# 💾 Vault Disk Stats
@app.route("/bitty/vault")
def bitty_vault():
    return render_template("bitty_vault.html", stats=get_disk_stats())

# 🧹 Prune Cache
@app.route("/bitty/prune")
def bitty_prune():
    auto_prune()
    return "🧹 Vault pruned."

# 📦 Export Snapshot
@app.route("/bitty/export")
def bitty_export():
    export_snapshot()
    return "📦 Snapshot exported."

# 🕰️ Timeline Views
@app.route("/codex/timeline")
@app.route("/codex/timeline/stream")
def codex_timeline():
    with open("cathedral_codex/codex_timeline.json", "r", encoding="utf-8") as f:
        timeline = json.load(f)
    template = "timeline_stream.html" if request.path.endswith("stream") else "timeline.html"
    return render_template(template, timeline=timeline)

# 📜 File Viewer
@app.route("/view")
def view_file():
    file_path = request.args.get("file", "")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f"<pre>{f.read()}</pre>"
    return f"File '{file_path}' not found.", 404

if __name__ == "__main__":
    app.run(debug=True)
