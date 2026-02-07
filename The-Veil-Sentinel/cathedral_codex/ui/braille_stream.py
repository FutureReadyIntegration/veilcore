from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix
from core.braille import glyph_to_audio

braille_bp = Blueprint("braille_stream", __name__)

@braille_bp.route("/braille-stream")
def braille_stream():
    recent = render_glyph_matrix()[-20:]
    converted = []

    for e in recent:
        audible = glyph_to_audio(e["glyph"])
        converted.append({
            "timestamp": e["timestamp"],
            "user":      e.get("user", "unknown"),
            "method":    e.get("method", "audit"),
            "phrase":    audible,
            "urgent":    e.get("urgent", False)
        })

    return render_template("braille_stream.html", entries=converted)
