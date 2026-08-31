"""initial_schema

Revision ID: 463ea894ae63
Revises:
Create Date: 2026-08-12 15:51:39.959989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '463ea894ae63'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), default='New Conversation'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), default='pending_validation'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('publisher', sa.String(255), nullable=True),
        sa.Column('isbn_reference', sa.String(100), nullable=True),
        sa.Column('source_trusted', sa.Boolean(), nullable=True),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('admin_approved', sa.Boolean(), default=False),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )

    # Feedback table (RLHF Golden Dataset)
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('message_id', sa.String(36), nullable=False),
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('is_positive', sa.Boolean(), nullable=False),
        sa.Column('original_question', sa.Text(), nullable=False),
        sa.Column('ai_answer', sa.Text(), nullable=False),
        sa.Column('user_correction', sa.Text(), nullable=True),
        sa.Column('error_category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_table('documents')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
