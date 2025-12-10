"""Service for matching streets to default street dictionary."""

from app.models.street import Street


class StreetMatchingService:
    """Service for matching streets from different decades to default street dictionary."""

    def __init__(self, db_session):
        """Initialize the service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def get_default_streets_lookup(self, user_id, city):
        """Build lookup dictionary of default streets for a city.

        Args:
            user_id: User ID
            city: City name

        Returns:
            tuple: (lookup_dict, default_streets_list) where lookup_dict maps
                   (prefix, main_name) tuples to Street objects
        """
        default_streets = Street.query.filter_by(
            user_id=user_id, city=city, is_default_street=True, is_rejected=False
        ).all()

        lookup = {}
        for default_street in default_streets:
            key = (default_street.prefix, default_street.main_name)
            lookup[key] = default_street

        return lookup, default_streets

    def find_unmatched_source_streets(self, user_id, city, decade):
        """Get source streets that need matching for a specific decade.

        Args:
            user_id: User ID
            city: City name
            decade: Decade string (e.g. '1940-1949')

        Returns:
            list: List of Street objects that need matching
        """
        source_streets = (
            Street.query.filter_by(
                user_id=user_id,
                city=city,
                decade=decade,
                is_default_street=False,
                is_rejected=False,
            )
            .filter(Street.default_street_id.is_(None))
            .order_by(Street.main_name)
            .all()
        )

        return source_streets

    def match_streets(self, source_streets, default_lookup, save=False):
        """Match source streets to default streets using lookup dictionary.

        Args:
            source_streets: List of Street objects to match
            default_lookup: Dictionary mapping (prefix, main_name) to Street objects
            save: If True, save matches to database

        Returns:
            tuple: (matches, not_matched) where:
                - matches is a list of (source_street, default_street) tuples
                - not_matched is a list of source streets with no match
        """
        matches = []
        not_matched = []

        for source_street in source_streets:
            key = (source_street.prefix, source_street.main_name)
            default_street = default_lookup.get(key)

            if default_street:
                matches.append((source_street, default_street))

                if save:
                    # Update the mapping
                    source_street.default_street_id = default_street.id
                    self.db.add(source_street)
            else:
                not_matched.append(source_street)

        # Commit all changes if saving
        if save and matches:
            self.db.commit()

        return matches, not_matched
