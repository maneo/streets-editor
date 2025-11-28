"""Street dictionary models."""

from datetime import datetime

from app import db


class Street(db.Model):
    """Street model in the dictionary."""

    __tablename__ = "streets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Session metadata
    city = db.Column(db.String(100), nullable=False)
    decade = db.Column(db.String(20), nullable=False)  # e.g. "1940-1949"

    # Street data
    prefix = db.Column(db.String(10), default="ul.")  # ul., pl., al., -
    main_name = db.Column(db.String(200), nullable=False)  # lowercase version
    main_name_cs = db.Column(
        db.String(200), nullable=False
    )  # case-sensitive version from extraction
    variants = db.Column(db.Text, default="")  # JSON array as string
    misspellings = db.Column(db.Text, default="")  # JSON array as string

    # Metadata
    is_rejected = db.Column(db.Boolean, default=False)
    source = db.Column(db.String(20), default="ai")  # ai, manual
    source_map_id = db.Column(db.Integer, db.ForeignKey("source_maps.id"), nullable=True)
    is_default_street = db.Column(db.Boolean, default=False)
    default_street_id = db.Column(db.Integer, db.ForeignKey("streets.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    street_content = db.relationship(
        "StreetContent", backref="street", uselist=False, cascade="all, delete-orphan"
    )
    mapped_to_default_street = db.relationship(
        "Street", remote_side=[id], foreign_keys=[default_street_id]
    )

    # Index for uniqueness (city + decade + main_name for given user)
    __table_args__ = (
        db.Index("idx_user_city_decade_name", "user_id", "city", "decade", "main_name"),
    )

    def __repr__(self):
        return f"<Street {self.prefix} {self.main_name}>"

    def to_dict(self, include_default_street=False):
        """Convert street to dictionary for editor and general API use."""
        import json

        variants = json.loads(self.variants) if self.variants else []
        misspellings = json.loads(self.misspellings) if self.misspellings else []

        display_prefix = "" if not self.prefix or self.prefix == "-" else f"{self.prefix} "

        result = {
            "id": self.id,
            "user_id": self.user_id,
            "city": self.city,
            "decade": self.decade,
            "prefix": self.prefix,
            "main_name": self.main_name,  # Use lowercase version for API consistency
            "main_name_cs": self.main_name_cs,
            "display_name": f"{display_prefix}{self.main_name_cs}".strip(),
            "variants": variants,
            "misspellings": misspellings,
            "is_rejected": self.is_rejected,
            "source": self.source,
            "is_default_street": self.is_default_street,
            "default_street_id": self.default_street_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include mapped street info if exists
        if self.mapped_to_default_street:
            result["mapped_to_default_street"] = {
                "id": self.mapped_to_default_street.id,
                "display_name": f"{'' if not self.mapped_to_default_street.prefix or self.mapped_to_default_street.prefix == '-' else f'{self.mapped_to_default_street.prefix} '}{self.mapped_to_default_street.main_name_cs}".strip(),
            }

        if include_default_street and self.street_content:
            result["street_content"] = self.street_content.to_dict()

        return result

    def to_dict_export(self):
        """Convert street to dictionary for dictionary export APIs (JSON/TXT)."""
        import json

        variants = json.loads(self.variants) if self.variants else []
        misspellings = json.loads(self.misspellings) if self.misspellings else []

        display_prefix = "" if not self.prefix or self.prefix == "-" else f"{self.prefix} "

        return {
            "id": self.id,
            "user_id": self.user_id,
            "city": self.city,
            "decade": self.decade,
            "prefix": self.prefix,
            "main_name": (self.main_name or "").lower(),  # Use lowercase version for exports
            "main_name_cs": self.main_name_cs,
            "display_name": f"{display_prefix}{self.main_name_cs}".strip(),
            "variants": variants,
            "misspellings": misspellings,
            "is_rejected": self.is_rejected,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
