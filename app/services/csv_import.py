"""CSV street import service."""

import csv

from flask import current_app

from app import db
from app.models.street import ALLOWED_PREFIXES, Street

# Maximum prefix length in database
MAX_PREFIX_LENGTH = 10


def _normalize_prefix(prefix: str) -> tuple[str, bool]:
    """Normalize prefix to canonical lowercase form; return (prefix, is_known)."""
    raw = (prefix or "").strip().lower()
    if not raw:
        return "ul.", True

    # Normalize dotted variants
    dotted_map = {
        "ul": "ul.",
        "ul.": "ul.",
        "al": "al.",
        "al.": "al.",
        "pl": "pl.",
        "pl.": "pl.",
        "os": "os.",
        "os.": "os.",
    }
    canonical = dotted_map.get(raw, raw)

    # Truncate to max length if needed
    if len(canonical) > MAX_PREFIX_LENGTH:
        canonical = canonical[:MAX_PREFIX_LENGTH]

    is_known = canonical in ALLOWED_PREFIXES
    return canonical, is_known


def import_streets_from_csv(
    filepath: str, user_id: int, city: str, decade: str
) -> dict[str, object]:
    """
    Import streets from CSV.

    CSV columns: city, prefix, street_name_cs, district
    - City mismatch rows are skipped (counted).
    - Duplicate streets (same user/city/decade/name) update prefix/district/name.
    """
    inserted = 0
    updated = 0
    skipped_city = 0
    errors: list[str] = []
    unknown_prefixes: set[str] = set()

    batch_size = current_app.config["BATCH_INSERT_SIZE"]
    processed_since_commit = 0

    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row_num, row in enumerate(reader, start=1):
            if len(row) != 4:
                errors.append(
                    f"Row {row_num}: expected 4 columns (city,prefix,street_name_cs,district), got {len(row)}."
                )
                continue

            row_city, prefix_raw, name_cs, district = [col.strip() for col in row[:4]]

            if row_city and row_city.lower() != city.lower():
                skipped_city += 1
                continue

            if not name_cs:
                errors.append(f"Row {row_num}: street_name_cs is required.")
                continue

            prefix, is_known_prefix = _normalize_prefix(prefix_raw)
            if not is_known_prefix:
                # Store original prefix (before truncation) for tracking
                original_prefix = prefix_raw.strip() if prefix_raw else ""
                if original_prefix:
                    unknown_prefixes.add(original_prefix)

            main_name_lower = name_cs.lower()
            district_value = district or None

            existing = Street.query.filter_by(
                user_id=user_id, city=city, decade=decade, main_name=main_name_lower
            ).first()

            if existing:
                existing.prefix = prefix
                existing.main_name = main_name_lower
                existing.main_name_cs = name_cs
                existing.district = district_value
                existing.source = "csv"
                existing.is_rejected = False
                updated += 1
            else:
                street = Street(
                    user_id=user_id,
                    city=city,
                    decade=decade,
                    prefix=prefix,
                    main_name=main_name_lower,
                    main_name_cs=name_cs,
                    district=district_value,
                    source="csv",
                )
                db.session.add(street)
                inserted += 1

            processed_since_commit += 1
            if processed_since_commit >= batch_size:
                try:
                    db.session.commit()
                except Exception as commit_error:
                    db.session.rollback()
                    raise commit_error
                else:
                    processed_since_commit = 0

    # Final commit for remaining rows
    try:
        db.session.commit()
    except Exception as commit_error:
        db.session.rollback()
        raise commit_error

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped_city": skipped_city,
        "errors": errors,
        "unknown_prefixes": sorted(unknown_prefixes),
    }
