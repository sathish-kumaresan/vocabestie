"""add_learning_session_tables

Revision ID: c8f3a2b1d4e5
Revises: 515e139c0ee3
Create Date: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f3a2b1d4e5'
down_revision: Union[str, None] = '515e139c0ee3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create word_review_state table (SM2 per-word tracking)
    op.create_table('word_review_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('easiness_factor', sa.Float(), nullable=True, server_default='2.5'),
        sa.Column('sm2_interval', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sm2_repetitions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['word_id'], ['words.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'word_id', name='uq_user_word_review')
    )
    op.create_index('ix_word_review_user_date', 'word_review_state', ['user_id', 'next_review_date'], unique=False)

    # Create learning_session table
    op.create_table('learning_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scenario_id', sa.Integer(), nullable=False),
        sa.Column('total_exercises', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_session_user_status', 'learning_session', ['user_id', 'status'], unique=False)

    # Create exercise_queue table
    op.create_table('exercise_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('skill_type', sa.String(length=10), nullable=False),
        sa.Column('queue_type', sa.String(length=10), nullable=False),
        sa.Column('queue_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('was_correct', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['learning_session.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['word_id'], ['words.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'word_id', 'skill_type', name='uq_session_word_skill')
    )
    op.create_index('ix_queue_session_order', 'exercise_queue', ['session_id', 'queue_order'], unique=False)
    op.create_index('ix_queue_session_status', 'exercise_queue', ['session_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_queue_session_status', table_name='exercise_queue')
    op.drop_index('ix_queue_session_order', table_name='exercise_queue')
    op.drop_table('exercise_queue')
    op.drop_index('ix_session_user_status', table_name='learning_session')
    op.drop_table('learning_session')
    op.drop_index('ix_word_review_user_date', table_name='word_review_state')
    op.drop_table('word_review_state')
