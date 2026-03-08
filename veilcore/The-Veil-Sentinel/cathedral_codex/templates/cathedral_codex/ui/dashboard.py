from flask import Blueprint, render_template
from core.glyph_matrix import render_glyph_matrix

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/glyph-dashboard")
def glyph_dashboard():
    matrix = render_glyph_matrix()
    return render_template("glyph_grid.html", matrix=matrix)
