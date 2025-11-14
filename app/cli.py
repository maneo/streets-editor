"""Flask CLI commands for development and testing."""

import click

from app import db
from app.models.street import Street
from app.models.user import User


def register_cli_commands(app):
    """Register Flask CLI commands."""

    @app.cli.command("create-test-user")
    @click.option("--email", default="test@example.com", help="User email")
    @click.option("--password", default="password123", help="User password")
    def create_test_user(email, password):
        """Create a test user for development and testing.

        Usage:
            flask create-test-user
            flask create-test-user --email admin@test.com --password admin123
        """
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            click.echo(f"User with email '{email}' already exists.")
            return

        # Create new user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        click.echo("Test user created successfully!")
        click.echo(f"  Email: {email}")
        click.echo(f"  Password: {password}")
        click.echo(f"  User ID: {user.id}")

    @app.cli.command("clear-db")
    @click.confirmation_option(prompt="Are you sure you want to delete all data?")
    def clear_database():
        """Clear all data from database (requires confirmation).

        Usage:
            flask clear-db
        """
        # Delete all streets
        num_streets = Street.query.delete()

        # Delete all users
        num_users = User.query.delete()

        db.session.commit()

        click.echo("Database cleared!")
        click.echo(f"  Deleted {num_users} users")
        click.echo(f"  Deleted {num_streets} streets")

    @app.cli.command("list-users")
    def list_users():
        """List all users in the database.

        Usage:
            flask list-users
        """
        users = User.query.all()

        if not users:
            click.echo("No users found in database.")
            return

        click.echo(f"Found {len(users)} user(s):")
        click.echo()

        for user in users:
            street_count = Street.query.filter_by(user_id=user.id, is_rejected=False).count()
            click.echo(f"  ID: {user.id}")
            click.echo(f"  Email: {user.email}")
            click.echo(f"  Created: {user.created_at}")
            click.echo(f"  Streets: {street_count}")
            click.echo()
