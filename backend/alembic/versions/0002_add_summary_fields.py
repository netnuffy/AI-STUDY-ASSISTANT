"""Add key_concepts and important_questions to summaries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "summaries",
        sa.Column("key_concepts", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "summaries",
        sa.Column(
            "important_questions", sa.JSON(), nullable=False, server_default="[]"
        ),
    )


def downgrade() -> None:
    op.drop_column("summaries", "important_questions")
    op.drop_column("summaries", "key_concepts")
