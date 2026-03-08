from flask import Blueprint, render_template, request
from core.glyph_matrix import render_glyph_matrix

gallery_bp = Blueprint("user_gallery", __name__)

@gallery_bp.route("/user/<user_id>/badges")
def user_badges(user_id):
    method = request.args.get("method")
    lang   = request.args.get("lang")

    entries = render_glyph_matrix()
    filtered = []

    for e in entries:
        match = True
        if method and method != e.get("method"): match = False
        if lang and lang != e.get("language"):  match = False
        if user_id != e.get("user"): match = False
        if match: filtered.append(e)

    return render_template("user_badges.html", entries=filtered, user_id=user_id)
