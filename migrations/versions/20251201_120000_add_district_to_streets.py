"""Add district column to Street

Revision ID: 20251201_120000
Revises: 20251128_120000
Create Date: 2025-12-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251201_120000'
down_revision = '20251128_120000'
branch_labels = None
depends_on = None


def upgrade():
    # Import inspector early to check existing state
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('streets')]

    # Add district column to streets table if it doesn't exist
    if 'district' not in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('district', sa.String(length=100), nullable=True))


def downgrade():
    # Remove district column from streets table
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('streets')]

    if 'district' in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.drop_column('district')
