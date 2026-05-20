"""replace date_of_birth with age, drop kata/kumite FK columns

Revision ID: 9a8b7c6d5e4f
Revises: 3d5e8a1b2c9f
Create Date: 2026-05-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "3d5e8a1b2c9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: replace date_of_birth with age, drop FK columns."""
    # Step 1: add nullable age column (safe on all SQLite versions)
    op.add_column("athletes", sa.Column("age", sa.Integer(), nullable=True))

    # Step 2: migrate existing data — compute age from date_of_birth
    op.execute(
        """
        UPDATE athletes
        SET age = CAST(
            (julianday('now') - julianday(date_of_birth)) / 365.25 AS INTEGER
        )
        WHERE date_of_birth IS NOT NULL
        """
    )

    # Step 3: apply remaining changes in batch (required for SQLite DROP COLUMN)
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.alter_column(
            "age", existing_type=sa.Integer(), nullable=False
        )
        batch_op.drop_index("ix_athletes_date_of_birth")
        batch_op.drop_column("date_of_birth")
        batch_op.drop_column("kata_category_id")
        batch_op.drop_column("kumite_category_id")


def downgrade() -> None:
    """Downgrade: restore date_of_birth and FK columns."""
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("date_of_birth", sa.Date(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kata_category_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kumite_category_id", sa.Integer(), nullable=True)
        )

    # approximate restoration — cannot recover original dates
    op.execute(
        """
        UPDATE athletes
        SET date_of_birth = date('now', '-' || age || ' years')
        WHERE age IS NOT NULL
        """
    )

    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.alter_column(
            "date_of_birth", existing_type=sa.Date(), nullable=False
        )
        batch_op.create_index("ix_athletes_date_of_birth", ["date_of_birth"])
        batch_op.drop_column("age")
