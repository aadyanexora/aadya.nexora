"""add metadata columns to document_chunks

Revision ID: 0003_add_chunk_metadata
Revises: 0002_add_credits_usage_logs
Create Date: 2026-03-04 05:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_chunk_metadata'
down_revision = '0002_add_credits_usage_logs'
branch_labels = None
depend_on = None


def upgrade():
    op.add_column('document_chunks', sa.Column('source', sa.String(), nullable=True))
    op.add_column('document_chunks', sa.Column('filename', sa.String(), nullable=True))
    op.add_column('document_chunks', sa.Column('page', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('document_chunks', 'page')
    op.drop_column('document_chunks', 'filename')
    op.drop_column('document_chunks', 'source')
