from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix

carousel_bp = Blueprint("glyph_carousel", __name__)

@carousel_bp.route("/glyph-carousel")
def glyph_carousel():
    recent = render_glyph_matrix()[-15:]
    return render_template("glyph_carousel.html", entries=recent)
