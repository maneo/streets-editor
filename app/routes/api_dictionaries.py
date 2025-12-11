"""API routes for listing and exporting street dictionaries."""

import io
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import case, func

from app import db
from app.models.street import Street
from app.services.export_service import generate_txt_export

bp = Blueprint("api_dictionaries", __name__, url_prefix="/api")


def _json_error(message, status_code):
    return jsonify({"error": message}), status_code


def _parse_positive_int(value, default, field_name):
    if value is None:
        return default
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{field_name} must be an integer.") from err

    if parsed_value < 1:
        raise ValueError(f"{field_name} must be greater than 0.")

    return parsed_value


def _apply_source_filter(query, source):
    if not source:
        return query

    if source not in {"ai", "manual"}:
        raise ValueError("source must be either 'ai' or 'manual'.")

    return query.filter(Street.source == source)


@bp.route("/dictionaries", methods=["GET"])
@login_required
def list_dictionaries():
    """Return aggregated list of dictionaries for the current user."""
    aggregates = (
        Street.query.with_entities(
            Street.city,
            Street.decade,
            func.count(Street.id).label("street_count"),
            func.sum(case((Street.source == "ai", 1), else_=0)).label("ai_generated"),
            func.sum(case((Street.source == "manual", 1), else_=0)).label("manually_added"),
            func.max(Street.updated_at).label("last_modified"),
        )
        .filter_by(user_id=current_user.id, is_rejected=False)
        .group_by(Street.city, Street.decade)
        .order_by(func.lower(Street.city).asc(), Street.decade.desc())
        .all()
    )

    dictionaries = []
    total_streets = 0

    for row in aggregates:
        last_modified = (
            row.last_modified.isoformat() if isinstance(row.last_modified, datetime) else None
        )
        street_count = row.street_count or 0

        dictionaries.append(
            {
                "city": row.city,
                "decade": row.decade,
                "street_count": street_count,
                "ai_generated": row.ai_generated or 0,
                "manually_added": row.manually_added or 0,
                "last_modified": last_modified,
            }
        )
        total_streets += street_count

    return jsonify(
        {
            "dictionaries": dictionaries,
            "total_dictionaries": len(dictionaries),
            "total_streets": total_streets,
        }
    )


@bp.route("/dictionaries/<city>/<decade>/streets/json", methods=["GET"])
@login_required
def dictionary_streets_json(city, decade):
    """Return paginated JSON list of streets for a dictionary."""
    try:
        page = _parse_positive_int(request.args.get("page"), 1, "page")
        per_page = _parse_positive_int(request.args.get("per_page"), 50, "per_page")
    except ValueError as exc:
        return _json_error(str(exc), 400)

    per_page = min(per_page, 100)
    source = request.args.get("source")

    base_query = Street.query.filter_by(
        user_id=current_user.id,
        city=city,
        decade=decade,
        is_rejected=False,
    ).order_by(Street.main_name)

    try:
        filtered_query = _apply_source_filter(base_query, source)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    pagination = filtered_query.paginate(page=page, per_page=per_page, error_out=False)

    if pagination.total == 0:
        return _json_error("No streets found for this dictionary.", 404)

    streets_payload = [street.to_dict_export() for street in pagination.items]

    response_payload = {
        "dictionary": {
            "city": city,
            "decade": decade,
            "total_streets": pagination.total,
            "source_filter": source,
        },
        "streets": streets_payload,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
        },
    }

    return jsonify(response_payload)


@bp.route("/dictionaries/<city>/<decade>/streets/txt", methods=["GET"])
@login_required
def dictionary_streets_txt(city, decade):
    """Return TXT export for a dictionary (optionally filtered by source)."""
    source = request.args.get("source")

    base_query = Street.query.filter_by(
        user_id=current_user.id,
        city=city,
        decade=decade,
        is_rejected=False,
    ).order_by(Street.main_name)

    try:
        filtered_query = _apply_source_filter(base_query, source)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    streets = filtered_query.all()

    if not streets:
        return _json_error("No streets found for this dictionary.", 404)

    txt_content = generate_txt_export(streets)
    txt_file = io.BytesIO(txt_content.encode("utf-8"))
    txt_file.seek(0)

    filename = f"{city}_{decade}_streets.txt"

    return send_file(
        txt_file,
        mimetype="text/plain",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/dictionaries/<city>/<decade>/set-default", methods=["PUT"])
@login_required
def set_default_dictionary(city, decade):
    """Set a dictionary as default for a city. Only one dictionary per city can be default."""

    # Verify that the dictionary exists and belongs to the current user
    streets = Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade, is_rejected=False
    ).all()

    if not streets:
        return _json_error("Dictionary not found or has no active streets.", 404)

    # Find all streets in other dictionaries for this city that are currently default
    other_default_streets = (
        Street.query.filter_by(user_id=current_user.id, city=city, is_default_street=True)
        .filter(Street.decade != decade)
        .all()
    )

    # Remove street_content for streets that are no longer default
    for street in other_default_streets:
        if street.street_content:
            db.session.delete(street.street_content)

    # Set is_default_street=False for all other dictionaries in this city
    Street.query.filter_by(user_id=current_user.id, city=city, is_default_street=True).update(
        {"is_default_street": False}, synchronize_session=False
    )

    # Set is_default_street=True for all streets in the selected dictionary
    Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade, is_rejected=False
    ).update({"is_default_street": True}, synchronize_session=False)

    db.session.commit()

    return jsonify(
        {
            "message": f"Dictionary '{city} {decade}' set as default successfully.",
            "city": city,
            "decade": decade,
            "streets_updated": len(streets),
        }
    ), 200


@bp.route("/dictionaries/<city>/<decade>", methods=["DELETE"])
@login_required
def delete_dictionary(city, decade):
    """Delete all streets and source maps for a dictionary (city + decade combination)."""
    from app.models.source_maps import SourceMaps

    # Verify that the dictionary exists and belongs to the current user
    streets_count = Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade, is_rejected=False
    ).count()

    if streets_count == 0:
        return _json_error("Dictionary not found or no streets to delete.", 404)

    # Delete all streets (hard delete)
    # 1. Find IDs of streets in this dictionary
    streets_to_delete_ids = [
        s.id
        for s in Street.query.with_entities(Street.id).filter_by(
            user_id=current_user.id, city=city, decade=decade
        )
    ]

    if streets_to_delete_ids:
        # 2. Nullify default_street_id references in other streets that point to these IDs
        Street.query.filter(Street.default_street_id.in_(streets_to_delete_ids)).update(
            {"default_street_id": None}, synchronize_session=False
        )

    # Delete associated street content for streets being removed
    if streets_to_delete_ids:
        from app.models.street_content import StreetContent

        StreetContent.query.filter(StreetContent.street_id.in_(streets_to_delete_ids)).delete(
            synchronize_session=False
        )

    # 3. Delete the streets themselves
    deleted_total = Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade
    ).delete(synchronize_session=False)

    # In some database backends delete() may return 0 despite rows being deleted (e.g., when
    # rowcount propagation is disabled). Fall back to previously counted active streets.
    if deleted_total == 0:
        deleted_total = streets_count

    # Delete associated source maps (hard delete)
    SourceMaps.query.filter_by(user_id=current_user.id, city=city, decade=decade).delete()

    # Commit all changes
    db.session.commit()

    return jsonify(
        {
            "message": f"Dictionary '{city} {decade}' and all associated data deleted successfully.",
            "deleted_streets": deleted_total,
            "deleted_active_streets": streets_count,
        }
    ), 200
