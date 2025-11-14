"""Export routes for TXT and JSON formats."""

import io

from flask import Blueprint, abort, request, send_file
from flask_login import current_user, login_required

from app.models.street import Street
from app.services.export_service import generate_json_export, generate_txt_export

bp = Blueprint("export", __name__, url_prefix="/export")


@bp.route("/txt")
@login_required
def export_txt():
    """Export streets as TXT file (one street per line)."""
    city = request.args.get("city")
    decade = request.args.get("decade")

    if not city or not decade:
        abort(400, "City and decade parameters are required.")

    # Get streets for this city and decade
    streets = (
        Street.query.filter_by(user_id=current_user.id, city=city, decade=decade, is_rejected=False)
        .order_by(Street.main_name)
        .all()
    )

    if not streets:
        abort(404, "No streets found for this city and decade.")

    # Generate TXT content
    txt_content = generate_txt_export(streets)

    # Create file-like object
    txt_file = io.BytesIO(txt_content.encode("utf-8"))
    txt_file.seek(0)

    filename = f"{city}_{decade}_streets.txt"

    return send_file(txt_file, mimetype="text/plain", as_attachment=True, download_name=filename)


@bp.route("/json")
@login_required
def export_json():
    """Export streets as JSON file."""
    city = request.args.get("city")
    decade = request.args.get("decade")

    if not city or not decade:
        abort(400, "City and decade parameters are required.")

    # Get streets for this city and decade
    streets = (
        Street.query.filter_by(user_id=current_user.id, city=city, decade=decade, is_rejected=False)
        .order_by(Street.main_name)
        .all()
    )

    if not streets:
        abort(404, "No streets found for this city and decade.")

    # Generate JSON content
    json_content = generate_json_export(streets, city, decade)

    # Create file-like object
    json_file = io.BytesIO(json_content.encode("utf-8"))
    json_file.seek(0)

    filename = f"{city}_{decade}_dictionary.json"

    return send_file(
        json_file, mimetype="application/json", as_attachment=True, download_name=filename
    )
