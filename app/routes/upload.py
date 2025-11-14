"""Upload and extraction routes."""

import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.street import Street
from app.services.ai_extraction import extract_streets_from_image
from app.services.file_handler import save_upload, validate_file

bp = Blueprint("upload", __name__)


@bp.route("/")
@login_required
def index():
    """Main upload page."""
    # Get user's streets grouped by city and decade
    streets = Street.query.filter_by(user_id=current_user.id, is_rejected=False).all()
    return render_template("upload.html", streets=streets)


@bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """Handle file upload and initiate extraction."""
    # Validate file
    if "file" not in request.files:
        flash("No file provided.", "error")
        return redirect(url_for("upload.index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("upload.index"))

    # Get city and decade
    city = request.form.get("city", "").strip()
    decade = request.form.get("decade", "").strip()

    if not city or not decade:
        flash("City and decade are required.", "error")
        return redirect(url_for("upload.index"))

    # Validate file
    validation_error = validate_file(file)
    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("upload.index"))

    # Save file
    filepath = save_upload(file, current_user.id)

    # Start extraction (this could be async in production)
    try:
        extracted_streets = extract_streets_from_image(filepath, city, decade)

        # Save extracted streets to database
        if not extracted_streets:
            flash("No streets found in the image. You can add them manually.", "warning")
        else:
            for street_data in extracted_streets:
                street = Street(
                    user_id=current_user.id,
                    city=city,
                    decade=decade,
                    prefix=street_data.get("prefix", "ul."),
                    main_name=street_data["main_name"].lower(),
                    main_name_cs=street_data["main_name"],
                    source="ai",
                )
                db.session.add(street)

            db.session.commit()
            flash(f"Successfully extracted {len(extracted_streets)} streets!", "success")

    except Exception as e:
        flash(f"Error during extraction: {str(e)}", "error")
    finally:
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for("upload.editor", city=city, decade=decade))


@bp.route("/editor/<city>/<decade>")
@login_required
def editor(city, decade):
    """Street editor page for a specific city and decade."""
    streets = (
        Street.query.filter_by(user_id=current_user.id, city=city, decade=decade, is_rejected=False)
        .order_by(Street.main_name)
        .all()
    )

    return render_template("editor.html", streets=streets, city=city, decade=decade)


@bp.route("/api/streets", methods=["POST"])
@login_required
def add_street():
    """Add a new street manually."""
    data = request.get_json()

    city = data.get("city")
    decade = data.get("decade")
    prefix = data.get("prefix", "ul.")
    main_name = data.get("main_name", "").strip()

    if not city or not decade or not main_name:
        return jsonify({"error": "City, decade, and main_name are required."}), 400

    # Check for duplicates
    existing = Street.query.filter_by(
        user_id=current_user.id, city=city, decade=decade, main_name=main_name.lower()
    ).first()

    if existing:
        return jsonify({"error": "Street already exists in this dictionary."}), 400

    # Create new street
    street = Street(
        user_id=current_user.id,
        city=city,
        decade=decade,
        prefix=prefix,
        main_name=main_name.lower(),
        main_name_cs=main_name,
        source="manual",
    )
    db.session.add(street)
    db.session.commit()

    return jsonify(
        {
            "id": street.id,
            "prefix": street.prefix,
            "main_name": street.main_name_cs,
            "source": street.source,
        }
    ), 201


@bp.route("/api/streets/<int:street_id>", methods=["PUT"])
@login_required
def update_street(street_id):
    """Update an existing street."""
    street = Street.query.get_or_404(street_id)

    # Ensure user owns this street
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    # Update fields
    if "prefix" in data:
        street.prefix = data["prefix"]
    if "main_name" in data:
        new_name = data["main_name"].strip()
        # Check for duplicates with new name
        existing = (
            Street.query.filter_by(
                user_id=current_user.id,
                city=street.city,
                decade=street.decade,
                main_name=new_name.lower(),
            )
            .filter(Street.id != street_id)
            .first()
        )

        if existing:
            return jsonify({"error": "Street with this name already exists."}), 400

        street.main_name = new_name.lower()
        street.main_name_cs = new_name

    if "variants" in data:
        import json

        street.variants = json.dumps(data["variants"])
    if "misspellings" in data:
        import json

        street.misspellings = json.dumps(data["misspellings"])

    db.session.commit()

    return jsonify({"message": "Street updated successfully."}), 200


@bp.route("/api/streets/<int:street_id>", methods=["DELETE"])
@login_required
def delete_street(street_id):
    """Mark street as rejected (soft delete)."""
    street = Street.query.get_or_404(street_id)

    # Ensure user owns this street
    if street.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    street.is_rejected = True
    db.session.commit()

    return jsonify({"message": "Street marked as rejected."}), 200
