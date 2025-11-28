"""Routes for managing default streets."""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models.street import Street

bp = Blueprint("default_streets", __name__)


@bp.route("/default-streets/<city>")
@login_required
def manage(city):
    """Manage default streets for a city (from the default dictionary)."""
    # Get default streets for the city (any decade that is marked as default)
    streets = (
        Street.query.filter_by(
            user_id=current_user.id, city=city, is_default_street=True, is_rejected=False
        )
        .order_by(Street.main_name)
        .all()
    )

    # Get the decade of the default dictionary (if any default streets exist)
    default_decade = streets[0].decade if streets else None

    return render_template(
        "default_streets.html", streets=streets, city=city, decade=default_decade
    )
