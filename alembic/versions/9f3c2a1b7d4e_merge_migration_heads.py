"""merge migration heads

Revision ID: 9f3c2a1b7d4e
Revises: 0070706263c6, d11e9b7f4a2c
Create Date: 2026-05-06 18:05:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "9f3c2a1b7d4e"
down_revision: Union[str, Sequence[str], None] = (
    "0070706263c6",
    "d11e9b7f4a2c",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
