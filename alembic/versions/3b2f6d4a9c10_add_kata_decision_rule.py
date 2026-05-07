"""add kata decision rule

Revision ID: 3b2f6d4a9c10
Revises: 08c34f5df417
Create Date: 2026-05-07 14:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3b2f6d4a9c10"
down_revision: Union[str, Sequence[str], None] = "08c34f5df417"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_column(inspector, "tournament_categories", "kata_decision_rule"):
        return

    op.add_column(
        "tournament_categories",
        sa.Column(
            "kata_decision_rule",
            sa.String(),
            nullable=False,
            server_default=sa.text("'average-with-discard'"),
        ),
    )

    op.execute(
        """
        UPDATE tournament_categories
        SET kata_decision_rule = 'average-with-discard'
        WHERE kata_decision_rule IS NULL OR kata_decision_rule = ''
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_column(inspector, "tournament_categories", "kata_decision_rule"):
        op.drop_column("tournament_categories", "kata_decision_rule")
