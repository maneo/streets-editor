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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for uniqueness (city + decade + main_name for given user)
    __table_args__ = (
        db.Index("idx_user_city_decade_name", "user_id", "city", "decade", "main_name"),
    )

    def __repr__(self):
        return f"<Street {self.prefix} {self.main_name}>"

    def to_dict(self):
        """Convert street to dictionary for JSON export and APIs."""
        import json

        variants = json.loads(self.variants) if self.variants else []
        misspellings = json.loads(self.misspellings) if self.misspellings else []

        display_prefix = "" if not self.prefix or self.prefix == "-" else f"{self.prefix} "

        return {
            "prefix": self.prefix,
            "main_name": (self.main_name or "").lower(),
            "main_name_cs": self.main_name_cs,
            "display_name": f"{display_prefix}{self.main_name_cs}".strip(),
            "variants": variants,
            "misspellings": misspellings,
        }
