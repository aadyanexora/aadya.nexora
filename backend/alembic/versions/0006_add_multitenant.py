"""add organizations and tenant columns

Revision ID: 0006_add_multitenant
Revises: 0005_add_refresh_tokens
Create Date: 2026-03-04 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0006_add_multitenant'
down_revision = '0005_add_refresh_tokens'
branch_labels = None
depend_on = None


def upgrade():
    # create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # add organization_id to users
    op.add_column('users', sa.Column('organization_id', sa.Integer(), nullable=True, index=True))
    op.create_foreign_key('fk_users_org', 'users', 'organizations', ['organization_id'], ['id'])
    # add organization_id to conversations
    op.add_column('conversations', sa.Column('organization_id', sa.Integer(), nullable=True, index=True))
    # add organization_id to documents and chunks
    op.add_column('documents', sa.Column('organization_id', sa.Integer(), nullable=True, index=True))
    op.add_column('document_chunks', sa.Column('organization_id', sa.Integer(), nullable=True, index=True))


def downgrade():
    # drop tenant columns and table
    op.drop_column('document_chunks', 'organization_id')
    op.drop_column('documents', 'organization_id')
    op.drop_column('conversations', 'organization_id')
    op.drop_constraint('fk_users_org', 'users', type_='foreignkey')
    op.drop_column('users', 'organization_id')
    op.drop_table('organizations')
