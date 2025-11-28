"""Add StreetContent model and default_street field to Street

Revision ID: 20251126_120000
Revises: 20251125_120000
Create Date: 2025-11-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251126_120000'
down_revision = '20251125_120000'
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

    # Add default_street column to streets table if it doesn't exist
    if 'default_street' not in columns:
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('default_street', sa.Boolean(), nullable=True, server_default='false'))

    # Remove old default_street_id column and related constraints/indexes if they exist
    # We need to check if they exist using raw SQL because batch_alter_table doesn't allow conditional operations

    if 'default_street_id' in columns:
        # Check if constraint exists before dropping
        fk_constraints = inspector.get_foreign_keys('streets')
        constraint_names = [fk['name'] for fk in fk_constraints]

        if 'fk_streets_default_street_id' in constraint_names:
            # Drop constraint using raw SQL since we're outside batch_alter_table
            op.execute('ALTER TABLE streets DROP CONSTRAINT IF EXISTS fk_streets_default_street_id')

        # Check if index exists
        indexes = inspector.get_indexes('streets')
        index_names = [idx['name'] for idx in indexes]

        if 'idx_streets_default_street_id' in index_names:
            op.drop_index('idx_streets_default_street_id', table_name='streets')

        # Drop column
        with op.batch_alter_table('streets', schema=None) as batch_op:
            batch_op.drop_column('default_street_id')

    # Create street_content table if it doesn't exist
    tables = inspector.get_table_names()
    if 'street_content' not in tables:
        op.create_table('street_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('street_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('external_links', sa.Text(), nullable=True, server_default=''),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=10), nullable=True),
        sa.Column('historical_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['street_id'], ['streets.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('street_id')
        )

        # Create index for street_id (already unique, but explicit index is good)
        op.create_index('idx_street_content_street_id', 'street_content', ['street_id'], unique=True)
    else:
        # Table exists, check if index exists
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('street_content')]
        if 'idx_street_content_street_id' not in existing_indexes:
            op.create_index('idx_street_content_street_id', 'street_content', ['street_id'], unique=True)


def downgrade():
    # Drop street_content table
    op.drop_index('idx_street_content_street_id', table_name='street_content')
    op.drop_table('street_content')

    # Remove default_street column from streets table
    with op.batch_alter_table('streets', schema=None) as batch_op:
        batch_op.drop_column('default_street')
