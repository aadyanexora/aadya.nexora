"""add organization_id to usage_logs

Revision ID: 0007_add_org_to_usage_logs
Revises: 0006_add_multitenant
Create Date: 2026-03-04 12:55:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_add_org_to_usage_logs'
down_revision = '0006_add_multitenant'
branch_labels = None
depend_on = None


def upgrade():
    op.add_column('usage_logs', sa.Column('organization_id', sa.Integer(), nullable=True, index=True))
    op.create_foreign_key('fk_usage_logs_org', 'usage_logs', 'organizations', ['organization_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_usage_logs_org', 'usage_logs', type_='foreignkey')
    op.drop_column('usage_logs', 'organization_id')
