"""API routes for managing street content (extended attributes for default streets)."""

import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.street import Street
from app.models.street_content import StreetContent

bp = Blueprint("api_street_content", __name__, url_prefix="/api")


@bp.route("/street-content/<int:street_id>", methods=["GET"])
@login_required
def get_street_content(street_id):
    """Get street content for a default street."""
    street = Street.query.get_or_404(street_id)

    # Verify street belongs to current user
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Verify street is a default street
    if not street.is_default_street:
        return jsonify({"error": "Street is not a default street."}), 400

    if street.street_content:
        return jsonify({"street_id": street_id, "content": street.street_content.to_dict()}), 200
    else:
        return jsonify({"street_id": street_id, "content": None}), 200


@bp.route("/street-content/<int:street_id>", methods=["POST", "PUT"])
@login_required
def upsert_street_content(street_id):
    """Create or update street content for a default street."""
    street = Street.query.get_or_404(street_id)

    # Verify street belongs to current user
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Verify street is a default street
    if not street.is_default_street:
        return jsonify({"error": "Street is not a default street."}), 400

    data = request.get_json()

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    external_links = data.get("external_links", [])
    district = data.get("district")
    postal_code = data.get("postal_code")
    historical_info = data.get("historical_info")

    # Check if content exists
    street_content = street.street_content

    if street_content:
        # Update existing
        if latitude is not None:
            street_content.latitude = latitude
        if longitude is not None:
            street_content.longitude = longitude
        if "external_links" in data:
            street_content.external_links = json.dumps(external_links)
        if "district" in data:
            street_content.district = district
        if "postal_code" in data:
            street_content.postal_code = postal_code
        if "historical_info" in data:
            street_content.historical_info = historical_info
        street_content.updated_by = current_user.id
    else:
        # Create new
        street_content = StreetContent(
            street_id=street_id,
            latitude=latitude,
            longitude=longitude,
            external_links=json.dumps(external_links),
            district=district,
            postal_code=postal_code,
            historical_info=historical_info,
            updated_by=current_user.id,
        )
        db.session.add(street_content)

    db.session.commit()

    return jsonify(street_content.to_dict()), 200 if street_content.id else 201


@bp.route("/street-content/<int:street_id>", methods=["DELETE"])
@login_required
def delete_street_content(street_id):
    """Delete street content for a default street."""
    street = Street.query.get_or_404(street_id)

    # Verify street belongs to current user
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Verify street is a default street
    if not street.is_default_street:
        return jsonify({"error": "Street is not a default street."}), 400

    if not street.street_content:
        return jsonify({"error": "Street content does not exist."}), 404

    db.session.delete(street.street_content)
    db.session.commit()

    return jsonify({"message": "Street content deleted successfully."}), 200
