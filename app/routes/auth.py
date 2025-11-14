"""Authentication routes - registration and login."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app import db
from app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate input
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("auth/register.html")

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("User with this email already exists.", "error")
            return render_template("auth/register.html")

        # Create new user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Auto login after registration
        login_user(user)
        flash("Registration successful! You have been automatically logged in.", "success")
        return redirect(url_for("upload.index"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate input
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("auth/login.html")

        # Find user and check password
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        # Login user
        login_user(user)
        flash("Logged in successfully!", "success")

        # Redirect to next page or upload
        next_page = request.args.get("next")
        return redirect(next_page) if next_page else redirect(url_for("upload.index"))

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    """User logout."""
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))
