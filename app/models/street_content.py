"""Street content model for extended attributes of default streets."""

import json
from datetime import datetime

from app import db


class StreetContent(db.Model):
    """Extended content for default streets (geolocation, links, etc.)."""

    __tablename__ = "street_content"

    id = db.Column(db.Integer, primary_key=True)
    street_id = db.Column(db.Integer, db.ForeignKey("streets.id"), nullable=False, unique=True)

    # Extended attributes
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    external_links = db.Column(db.Text, default="")  # JSON array as string
    district = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    historical_info = db.Column(db.Text, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<StreetContent for street_id={self.street_id}>"

    def to_dict(self):
        """Convert street content to dictionary."""
        external_links = json.loads(self.external_links) if self.external_links else []

        return {
            "id": self.id,
            "street_id": self.street_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "external_links": external_links,
            "district": self.district,
            "postal_code": self.postal_code,
            "historical_info": self.historical_info,
            "updated_by": self.updated_by,
            "has_geolocation": self.latitude is not None and self.longitude is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
