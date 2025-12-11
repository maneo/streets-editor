"""JSON street import service."""

import json

from flask import current_app

from app import db
from app.models.street import ALLOWED_PREFIXES, Street

# Maximum prefix length in database
MAX_PREFIX_LENGTH = 10

# Required fields in JSON structure
REQUIRED_FIELDS = {
    "main_name",
    "variants",
    "misspellings",
    "prefix",
    "display_name",
    "main_name_cs",
}


def _validate_street_object(street_obj: dict, index: int) -> str | None:
    """
    Validate a single street object from JSON.
    Returns error message if invalid, None if valid.
    """
    if not isinstance(street_obj, dict):
        return f"Street at index {index}: expected object, got {type(street_obj).__name__}"

    # Check for required fields
    missing_fields = REQUIRED_FIELDS - set(street_obj.keys())
    if missing_fields:
        return (
            f"Street at index {index}: missing required fields: {', '.join(sorted(missing_fields))}"
        )

    # Validate main_name
    main_name = street_obj.get("main_name")
    if not main_name or not isinstance(main_name, str) or not main_name.strip():
        return f"Street at index {index}: main_name is required and must be a non-empty string"

    # Validate main_name_cs
    main_name_cs = street_obj.get("main_name_cs")
    if not main_name_cs or not isinstance(main_name_cs, str) or not main_name_cs.strip():
        return f"Street at index {index}: main_name_cs is required and must be a non-empty string"

    # Validate variants (must be array)
    variants = street_obj.get("variants")
    if not isinstance(variants, list):
        return f"Street at index {index}: variants must be an array"

    # Validate misspellings (must be array)
    misspellings = street_obj.get("misspellings")
    if not isinstance(misspellings, list):
        return f"Street at index {index}: misspellings must be an array"

    # Validate prefix
    prefix = street_obj.get("prefix")
    if not isinstance(prefix, str):
        return f"Street at index {index}: prefix must be a string"

    # Normalize and validate prefix
    normalized_prefix = prefix.strip().lower() if prefix else "ul."
    if len(normalized_prefix) > MAX_PREFIX_LENGTH:
        normalized_prefix = normalized_prefix[:MAX_PREFIX_LENGTH]

    if normalized_prefix not in ALLOWED_PREFIXES:
        return f"Street at index {index}: invalid prefix '{prefix}'. Allowed prefixes: {', '.join(sorted(ALLOWED_PREFIXES))}"

    defaults_mapping = street_obj.get("defaults-mapping")
    if defaults_mapping is not None:
        if not isinstance(defaults_mapping, dict):
            return f"Street at index {index}: defaults-mapping must be an object"

        required_dm_fields = {"city", "decade", "main_name", "street_id"}
        missing_dm = required_dm_fields - set(defaults_mapping.keys())
        if missing_dm:
            return f"Street at index {index}: defaults-mapping missing required fields: {', '.join(sorted(missing_dm))}"

        # Field type validations
        city_val = defaults_mapping.get("city")
        decade_val = defaults_mapping.get("decade")
        main_name_val = defaults_mapping.get("main_name")
        street_id_val = defaults_mapping.get("street_id")

        if not isinstance(city_val, str) or not city_val.strip():
            return f"Street at index {index}: defaults-mapping.city must be a non-empty string"
        if not isinstance(decade_val, str) or not decade_val.strip():
            return f"Street at index {index}: defaults-mapping.decade must be a non-empty string"
        if not isinstance(main_name_val, str) or not main_name_val.strip():
            return f"Street at index {index}: defaults-mapping.main_name must be a non-empty string"
        if not isinstance(street_id_val, int) or street_id_val <= 0:
            return f"Street at index {index}: defaults-mapping.street_id must be a positive integer"

    return None


def import_streets_from_json(
    filepath: str, user_id: int, city: str, decade: str
) -> dict[str, object]:
    """
    Import streets from JSON file.

    JSON format: array of street objects with structure:
    {
        "main_name": "27 grudnia",
        "variants": ["27—go Grudnia"],
        "misspellings": ["27 grnri", "2710 grudnia"],
        "prefix": "ul.",
        "display_name": "ul. 27 Grudnia",
        "main_name_cs": "27 Grudnia"
    }

    Returns:
        Dictionary with import summary:
        - inserted: number of streets inserted
        - skipped: number of duplicate streets skipped
        - errors: list of error messages
    """
    inserted = 0
    skipped = 0
    errors: list[str] = []

    batch_size = current_app.config["BATCH_INSERT_SIZE"]
    processed_since_commit = 0

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON format: {str(e)}")
        return {"inserted": 0, "skipped": 0, "errors": errors}
    except Exception as e:
        errors.append(f"Failed to read JSON file: {str(e)}")
        return {"inserted": 0, "skipped": 0, "errors": errors}

    # Validate that data is an array
    if not isinstance(data, list):
        errors.append("JSON must contain an array of street objects")
        return {"inserted": 0, "skipped": 0, "errors": errors}

    # Process each street object
    for index, street_obj in enumerate(data):
        # Validate street object structure
        validation_error = _validate_street_object(street_obj, index)
        if validation_error:
            errors.append(validation_error)
            continue

        # Extract and normalize fields
        main_name_cs = street_obj["main_name_cs"].strip()
        main_name_lower = main_name_cs.lower()
        prefix = street_obj["prefix"].strip().lower() if street_obj["prefix"] else "ul."

        # Truncate prefix if needed
        if len(prefix) > MAX_PREFIX_LENGTH:
            prefix = prefix[:MAX_PREFIX_LENGTH]

        # Convert variants and misspellings to JSON strings
        variants_json = json.dumps(street_obj["variants"], ensure_ascii=False)
        misspellings_json = json.dumps(street_obj["misspellings"], ensure_ascii=False)

        defaults_mapping_obj = street_obj.get("defaults-mapping")
        default_street_id_val: int | None = None
        if defaults_mapping_obj:
            # Strict verification: match by provided street_id AND city/decade/name
            ref_street_id = defaults_mapping_obj["street_id"]
            ref_city = defaults_mapping_obj["city"].strip()
            ref_decade = defaults_mapping_obj["decade"].strip()
            ref_name = defaults_mapping_obj["main_name"].strip().lower()

            from sqlalchemy import and_

            default_street_query = Street.query.filter(
                and_(
                    Street.id == ref_street_id,
                    Street.is_default_street.is_(True),
                    Street.city == ref_city,
                    Street.decade == ref_decade,
                    Street.main_name == ref_name,
                )
            ).first()

            # Use ternary assignment per Ruff SIM108 recommendation
            default_street_id_val = default_street_query.id if default_street_query else None

        # Check for duplicates
        existing = Street.query.filter_by(
            user_id=user_id, city=city, decade=decade, main_name=main_name_lower
        ).first()

        if existing:
            skipped += 1
            continue

        # Create new street
        street = Street(
            user_id=user_id,
            city=city,
            decade=decade,
            prefix=prefix,
            main_name=main_name_lower,
            main_name_cs=main_name_cs,
            variants=variants_json,
            misspellings=misspellings_json,
            source="json",
            is_default_street=False,
            default_street_id=default_street_id_val,
        )
        db.session.add(street)
        inserted += 1

        processed_since_commit += 1
        if processed_since_commit >= batch_size:
            try:
                db.session.commit()
            except Exception as commit_error:
                db.session.rollback()
                errors.append(f"Database error during batch commit: {str(commit_error)}")
                # Continue processing remaining streets
            else:
                processed_since_commit = 0

    # Final commit for remaining rows
    if processed_since_commit > 0:
        try:
            db.session.commit()
        except Exception as commit_error:
            db.session.rollback()
            errors.append(f"Database error during final commit: {str(commit_error)}")

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
    }
