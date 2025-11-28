"""Upload and extraction routes."""

import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models.source_maps import SourceMaps
from app.models.street import Street
from app.services.ai_extraction import extract_streets_from_image
from app.services.file_handler import save_upload, validate_file

bp = Blueprint("upload", __name__)


def _get_default_dictionary_for_city(city, user_id):
    """Get the default dictionary (decade) for a given city."""
    # Find any street with is_default_street=True for this city
    default_street = Street.query.filter_by(
        user_id=user_id, city=city, is_default_street=True, is_rejected=False
    ).first()
    return default_street.decade if default_street else None


@bp.route("/")
@login_required
def index():
    """Main upload page."""
    # Get user's streets grouped by city and decade
    streets = Street.query.filter_by(user_id=current_user.id, is_rejected=False).all()

    # Build a map of city -> default decade
    default_dictionaries = {}
    cities = {street.city for street in streets}
    for city in cities:
        default_decade = _get_default_dictionary_for_city(city, current_user.id)
        if default_decade:
            default_dictionaries[city] = default_decade

    return render_template(
        "upload.html", streets=streets, default_dictionaries=default_dictionaries
    )


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

    # Create SourceMaps record first (to get ID for GCS filename)
    source_map = SourceMaps(
        user_id=current_user.id,
        city=city,
        decade=decade,
        original_filename=file.filename,
        gcs_filename="",  # Will be updated after upload
        gcs_url="",  # Will be updated after upload
    )
    db.session.add(source_map)
    db.session.commit()  # Commit to get the ID

    # Save file locally for extraction
    filepath = save_upload(file, current_user.id)

    # Start extraction (this could be async in production)
    try:
        extracted_streets = extract_streets_from_image(filepath, city, decade)
        # extracted_streets = []
        # time.sleep(10)

        # Save extracted streets to database
        if not extracted_streets:
            flash("No streets found in the image. You can add them manually.", "warning")
        else:
            current_app.logger.info(
                f"AI extraction completed, {len(extracted_streets)} streets found"
            )
            # Batch insert to prevent timeouts on hosted databases like Neon
            batch_size = current_app.config["BATCH_INSERT_SIZE"]
            inserted_count = 0

            for i in range(0, len(extracted_streets), batch_size):
                batch = extracted_streets[i : i + batch_size]

                for street_data in batch:
                    street = Street(
                        user_id=current_user.id,
                        city=city,
                        decade=decade,
                        prefix=street_data.get("prefix", "ul."),
                        main_name=street_data["main_name"].lower(),
                        main_name_cs=street_data["main_name"],
                        source="ai",
                        source_map_id=source_map.id,
                    )
                    db.session.add(street)

                try:
                    db.session.commit()
                    inserted_count += len(batch)
                except Exception as batch_error:
                    db.session.rollback()
                    current_app.logger.error(
                        f"Failed to insert batch starting at index {i}: {str(batch_error)}"
                    )
                    # Continue with next batch rather than failing completely
                    continue

                # Log successful batch insertion outside try block to avoid rollback
                current_app.logger.info(
                    f"Inserted batch of {len(batch)} streets ({inserted_count}/{len(extracted_streets)})"
                )

            if inserted_count > 0:
                # Upload file to GCS and update SourceMaps record
                try:
                    # Reset file pointer to beginning for GCS upload
                    file.seek(0)
                    gcs_filename, gcs_url = current_app.gcs_service.upload_file(
                        file, source_map.id, file.filename
                    )

                    # Update SourceMaps record with GCS info
                    source_map.gcs_filename = gcs_filename
                    source_map.gcs_url = gcs_url
                    source_map.streets_count = inserted_count
                    db.session.commit()

                    current_app.logger.info(f"File uploaded to GCS: {gcs_filename}")

                except Exception as gcs_error:
                    current_app.logger.error(f"Failed to upload file to GCS: {gcs_error}")
                    # Don't fail the whole process if GCS upload fails
                    flash(
                        "Warning: File extraction succeeded but could not be stored for verification.",
                        "warning",
                    )

                flash(f"Successfully extracted {inserted_count} streets!", "success")
                if inserted_count < len(extracted_streets):
                    flash(
                        f"Warning: {len(extracted_streets) - inserted_count} streets could not be saved due to database issues.",
                        "warning",
                    )
            else:
                flash("Failed to save any streets due to database issues.", "error")

    except Exception as e:
        error_msg = str(e)
        # Provide user-friendly messages for common errors
        if "Rate limit exceeded" in error_msg:
            flash(
                "AI extraction is temporarily rate limited. Please wait a few minutes and try again, or add streets manually.",
                "warning",
            )
        elif "API request failed" in error_msg:
            flash(
                "AI extraction service is currently unavailable. You can add streets manually.",
                "warning",
            )
        else:
            flash(f"Error during extraction: {error_msg}", "error")
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
        Street.query.options(joinedload(Street.mapped_to_default_street))
        .filter_by(user_id=current_user.id, city=city, decade=decade, is_rejected=False)
        .order_by(Street.main_name)
        .all()
    )

    # Get source map for this city/decade (if exists)
    source_map = SourceMaps.query.filter_by(
        user_id=current_user.id, city=city, decade=decade
    ).first()

    # Check if there's a default dictionary for this city
    default_street = Street.query.filter_by(
        user_id=current_user.id, city=city, is_default_street=True, is_rejected=False
    ).first()

    has_default_dictionary = default_street is not None
    is_current_default = default_street and default_street.decade == decade

    return render_template(
        "editor.html",
        streets=streets,
        city=city,
        decade=decade,
        source_map=source_map,
        has_default_dictionary=has_default_dictionary,
        is_current_default=is_current_default,
    )
