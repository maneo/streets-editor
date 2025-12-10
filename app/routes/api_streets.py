"""API routes for managing streets."""

import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.street import Street
from app.models.street_content import StreetContent
from app.services.geocoding_service import GeocodingService

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
    district = data.get("district")
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
        district=district or None,
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

    if "district" in data:
        street.district = data["district"] or None

    if "variants" in data:
        street.variants = json.dumps(data["variants"])
    if "misspellings" in data:
        street.misspellings = json.dumps(data["misspellings"])
    if "is_default_street" in data:
        street.is_default_street = bool(data["is_default_street"])

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


@bp.route("/default-streets/<city>", methods=["GET"])
@login_required
def get_default_streets(city):
    """Get default streets for a city (for mapping)."""
    search_query = request.args.get("search", "").strip().lower()

    # Get default streets for the city
    query = Street.query.filter_by(
        user_id=current_user.id, city=city, is_default_street=True, is_rejected=False
    )

    # Apply search filter if provided
    if search_query:
        query = query.filter(
            Street.main_name.contains(search_query) | Street.main_name_cs.contains(search_query)
        )

    streets = query.order_by(Street.main_name).all()

    result = []
    for street in streets:
        display_prefix = "" if not street.prefix or street.prefix == "-" else f"{street.prefix} "
        result.append(
            {
                "id": street.id,
                "display_name": f"{display_prefix}{street.main_name_cs}".strip(),
                "main_name": street.main_name_cs,
                "prefix": street.prefix,
            }
        )

    return jsonify({"streets": result}), 200


@bp.route("/streets/<int:street_id>/map-to-default", methods=["PUT"])
@login_required
def map_street_to_default(street_id):
    """Map a street to a default street."""
    street = Street.query.get_or_404(street_id)

    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    default_street_id = data.get("default_street_id")

    if not default_street_id:
        return jsonify({"error": "default_street_id is required."}), 400

    # Verify the default street exists and belongs to the same city
    default_street = Street.query.get_or_404(default_street_id)

    if default_street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    if default_street.city != street.city:
        return jsonify({"error": "Default street must be from the same city."}), 400

    if not default_street.is_default_street:
        return jsonify({"error": "Target street must be a default street."}), 400

    street.default_street_id = default_street_id
    db.session.commit()

    return jsonify(
        {
            "message": "Street mapped successfully.",
            "mapped_to": {
                "id": default_street.id,
                "display_name": f"{'' if not default_street.prefix or default_street.prefix == '-' else f'{default_street.prefix} '}{default_street.main_name_cs}".strip(),
            },
        }
    ), 200


@bp.route("/streets/<int:street_id>/map-to-default", methods=["DELETE"])
@login_required
def unmap_street_from_default(street_id):
    """Remove mapping from a street to default street."""
    street = Street.query.get_or_404(street_id)

    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    if not street.default_street_id:
        return jsonify({"error": "Street is not mapped to any default street."}), 400

    street.default_street_id = None
    db.session.commit()

    return jsonify({"message": "Street mapping removed successfully."}), 200


@bp.route("/streets/geolocations/<int:street_id>", methods=["POST"])
@login_required
def enrich_street_geolocation(street_id):
    """Enrich a single default street with geolocation data."""
    street = Street.query.get_or_404(street_id)

    # Verify street belongs to current user
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Verify street is a default street
    if not street.is_default_street:
        return jsonify({"error": "Street is not a default street."}), 400

    # Check if street already has geolocation
    if street.street_content and street.street_content.latitude and street.street_content.longitude:
        return jsonify(
            {
                "success": False,
                "message": "Street already has geolocation data.",
                "latitude": street.street_content.latitude,
                "longitude": street.street_content.longitude,
            }
        ), 200

    # Geocode the street
    geocoding_service = GeocodingService()
    result = geocoding_service.geocode_street(street.main_name_cs, street.city, street.prefix)

    if not result:
        return jsonify(
            {
                "success": False,
                "message": "Could not find geolocation for this street.",
            }
        ), 404

    # Create or update street content
    if street.street_content:
        street_content = street.street_content
        street_content.latitude = result["latitude"]
        street_content.longitude = result["longitude"]
        street_content.updated_by = current_user.id
    else:
        street_content = StreetContent(
            street_id=street.id,
            latitude=result["latitude"],
            longitude=result["longitude"],
            updated_by=current_user.id,
        )
        db.session.add(street_content)

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "message": "Geolocation enriched successfully.",
        }
    ), 200
