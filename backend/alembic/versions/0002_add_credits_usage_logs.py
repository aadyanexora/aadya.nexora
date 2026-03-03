"""add credits and usage_logs

Revision ID: 0002_add_credits_usage_logs
Revises: 0001_initial
Create Date: 2026-03-03 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_credits_usage_logs'
down_revision = '0001_initial'
branch_labels = None
depend_on = None


def upgrade():
    # add credits column to users with default 100
    op.add_column('users', sa.Column('credits', sa.Integer(), nullable=False, server_default='100'))

    # create usage_logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), index=True, nullable=True),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('usage_logs')
    op.drop_column('users', 'credits')
