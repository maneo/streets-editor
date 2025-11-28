"""Rename default_street column to is_default_street

Revision ID: 20251128_120000
Revises: 20251127_120000
Create Date: 2025-11-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251128_120000'
down_revision = '20251127_120000'
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

    # Rename default_street column to is_default_street if it exists
    if 'default_street' in columns and 'is_default_street' not in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.alter_column('default_street',
                                  new_column_name='is_default_street',
                                  existing_type=sa.Boolean(),
                                  existing_nullable=True,
                                  existing_server_default='false')


def downgrade():
    # Import inspector early to check existing state
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('streets')]

    # Rename is_default_street column back to default_street if it exists
    if 'is_default_street' in columns and 'default_street' not in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.alter_column('is_default_street',
                                  new_column_name='default_street',
                                  existing_type=sa.Boolean(),
                                  existing_nullable=True,
                                  existing_server_default='false')
