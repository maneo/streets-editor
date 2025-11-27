"""API routes for managing streets."""

import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.street import Street

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/streets", methods=["POST"])
@login_required
def add_street():
    """Add a new street manually."""
    data = request.get_json()

    city = data.get("city")
    decade = data.get("decade")
    prefix = data.get("prefix", "ul.")
    main_name_cs = data.get("main_name_cs", "").strip()
    variants = data.get("variants", [])
    misspellings = data.get("misspellings", [])

    if not city or not decade or not main_name_cs:
        return jsonify({"error": "City, decade, and main_name_cs are required."}), 400

    # Check for duplicates
    existing = Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade, main_name=main_name_cs.lower()
    ).first()

    if existing:
        return jsonify({"error": "Street already exists in this dictionary."}), 400

    street = Street(
        user_id=current_user.id,
        city=city,
        decade=decade,
        prefix=prefix,
        main_name=main_name_cs.lower(),
        main_name_cs=main_name_cs,
        variants=json.dumps(variants),
        misspellings=json.dumps(misspellings),
        source="manual",
    )
    db.session.add(street)
    db.session.commit()

    return jsonify(
        {
            "id": street.id,
            "prefix": street.prefix,
            "main_name": street.main_name_cs,
            "variants": variants,
            "misspellings": misspellings,
            "source": street.source,
        }
    ), 201


@bp.route("/streets/<int:street_id>", methods=["GET"])
@login_required
def get_street(street_id):
    """Get a single street."""
    street = Street.query.get_or_404(street_id)

    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(street.to_dict()), 200


@bp.route("/streets/<int:street_id>", methods=["PUT"])
@login_required
def update_street(street_id):
    """Update an existing street."""
    street = Street.query.get_or_404(street_id)

    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    if "prefix" in data:
        street.prefix = data["prefix"]
    if "main_name_cs" in data:
        new_name_cs = data["main_name_cs"].strip()
        existing = (
            Street.query.filter_by(
                user_id=current_user.id,
                city=street.city,
                decade=street.decade,
                main_name=new_name_cs.lower(),
            )
            .filter(Street.id != street_id)
            .first()
        )

        if existing:
            return jsonify({"error": "Street with this name already exists."}), 400

        street.main_name = new_name_cs.lower()
        street.main_name_cs = new_name_cs

    if "variants" in data:
        street.variants = json.dumps(data["variants"])
    if "misspellings" in data:
        street.misspellings = json.dumps(data["misspellings"])

    db.session.commit()

    return jsonify({"message": "Street updated successfully."}), 200


@bp.route("/streets/<int:street_id>", methods=["DELETE"])
@login_required
def delete_street(street_id):
    """Mark street as rejected (soft delete)."""
    street = Street.query.get_or_404(street_id)

    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    street.is_rejected = True
    db.session.commit()

    return jsonify({"message": "Street marked as rejected."}), 200
