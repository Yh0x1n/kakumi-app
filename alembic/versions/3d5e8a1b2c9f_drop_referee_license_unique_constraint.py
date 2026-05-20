"""drop unique constraint on referee license_number

Revision ID: 3d5e8a1b2c9f
Revises: 2c4f8d6b9a11
Create Date: 2026-05-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3d5e8a1b2c9f"
down_revision: Union[str, Sequence[str], None] = "2c4f8d6b9a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unique index and recreate as non-unique."""
    op.drop_index("ix_referees_license_number", table_name="referees")
    op.create_index(
        "ix_referees_license_number", "referees", ["license_number"], unique=False
    )


def downgrade() -> None:
    """Drop non-unique index and recreate as unique."""
    op.drop_index("ix_referees_license_number", table_name="referees")
    op.create_index(
        "ix_referees_license_number", "referees", ["license_number"], unique=True
    )
