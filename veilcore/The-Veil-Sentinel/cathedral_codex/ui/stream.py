from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix

stream_bp = Blueprint("glyph_stream", __name__)

@stream_bp.route("/glyph-stream")
def glyph_stream():
    recent = render_glyph_matrix()[-20:]
    return render_template("glyph_stream.html", entries=recent)
