"""add token/cost tracking and adjust user credits

Revision ID: 0004_add_usage_tracking
Revises: 0003_add_chunk_metadata
Create Date: 2026-03-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_usage_tracking'
down_revision = '0003_add_chunk_metadata'
branch_labels = None
depends_on = None


def upgrade():
    # users adjustments: bump default credits and add summary columns
    op.alter_column('users', 'credits', server_default='1000')
    # bump existing low-credit accounts up to the new default
    op.execute("UPDATE users SET credits=1000 WHERE credits < 1000")
    op.add_column('users', sa.Column('total_tokens_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_cost', sa.Float(), nullable=False, server_default='0'))

    # usage_logs modifications: add new fields and drop unused ones
    op.add_column('usage_logs', sa.Column('cost', sa.Float(), nullable=True))
    op.add_column('usage_logs', sa.Column('model_name', sa.String(), nullable=True))
    # drop legacy columns
    with op.batch_alter_table('usage_logs') as batch_op:
        batch_op.drop_column('endpoint')
        batch_op.drop_column('response_time_ms')


def downgrade():
    # reverse the above operations
    with op.batch_alter_table('usage_logs') as batch_op:
        batch_op.add_column(sa.Column('endpoint', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('response_time_ms', sa.Integer(), nullable=True))
    op.drop_column('usage_logs', 'model_name')
    op.drop_column('usage_logs', 'cost')

    op.drop_column('users', 'total_cost')
    op.drop_column('users', 'total_tokens_used')
    op.alter_column('users', 'credits', server_default='100')
