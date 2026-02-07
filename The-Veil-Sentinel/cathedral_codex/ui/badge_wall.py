from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix

badge_bp = Blueprint("badge_wall", __name__)

@badge_bp.route("/glyph-wall")
def glyph_wall():
    entries = render_glyph_matrix()
    return render_template("badge_wall.html", entries=entries)
