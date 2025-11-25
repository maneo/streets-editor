"""Source maps model for uploaded map images stored in Google Cloud Storage."""

from datetime import datetime

from app import db


class SourceMaps(db.Model):
    """Model for uploaded map images stored in Google Cloud Storage."""

    __tablename__ = "source_maps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    city = db.Column(db.String(100), nullable=False)
    decade = db.Column(db.String(20), nullable=False)

    # GCS storage info
    gcs_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    gcs_url = db.Column(db.Text, nullable=False)

    # Metadata
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    streets_count = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship("User", backref="source_maps")
    streets = db.relationship(
        "Street", backref="source_map", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SourceMap {self.id}: {self.city} {self.decade} - {self.original_filename}>"

    def to_dict(self):
        """Convert source map to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "city": self.city,
            "decade": self.decade,
            "gcs_filename": self.gcs_filename,
            "original_filename": self.original_filename,
            "gcs_url": self.gcs_url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "streets_count": self.streets_count,
        }
