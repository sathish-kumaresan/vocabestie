"""Add listening and spelling quiz types

Revision ID: f8d70ab8e03b
Revises: 1580946b7e01
Create Date: 2026-01-25 01:39:52.019864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8d70ab8e03b'
down_revision: Union[str, None] = '1580946b7e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to quiztype
    op.execute("ALTER TYPE quiztype ADD VALUE IF NOT EXISTS 'listening'")
    op.execute("ALTER TYPE quiztype ADD VALUE IF NOT EXISTS 'spelling'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the type and migrate data
    pass
