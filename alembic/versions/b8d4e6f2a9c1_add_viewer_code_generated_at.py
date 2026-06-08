"""add viewer_code_generated_at to tournaments

Revision ID: b8d4e6f2a9c1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8d4e6f2a9c1"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "viewer_code_generated_at",
                sa.DateTime(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("viewer_code_generated_at")
