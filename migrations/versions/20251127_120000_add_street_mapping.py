"""Add mapped_to_default_street_id field to Street

Revision ID: 20251127_120000
Revises: 20251126_120000
Create Date: 2025-11-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251127_120000'
down_revision = '20251126_120000'
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

    # Add default_street_id column to streets table if it doesn't exist
    if 'default_street_id' not in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('default_street_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_streets_default_street_id',
                'streets',
                ['default_street_id'],
                ['id']
            )


def downgrade():
    # Remove default_street_id column from streets table
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('streets')]

    if 'default_street_id' in columns:
        # Check if constraint exists before dropping
        fk_constraints = inspector.get_foreign_keys('streets')
        constraint_names = [fk['name'] for fk in fk_constraints]

        if 'fk_streets_default_street_id' in constraint_names:
            op.drop_constraint('fk_streets_default_street_id', 'streets', type_='foreignkey')

        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.drop_column('default_street_id')
