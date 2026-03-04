"""create refresh_tokens table for logout/rotation

Revision ID: 0005_add_refresh_tokens
Revises: 0004_add_usage_tracking
Create Date: 2026-03-04 07:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_refresh_tokens'
down_revision = '0004_add_usage_tracking'
branch_labels = None
depend_on = None


def upgrade():
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('refresh_tokens')
