"""add dim1 to natural key

Revision ID: a1b2c3d4e5f6
Revises: 0f4c1b60c958
Create Date: 2026-05-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0f4c1b60c958"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "health_metrics",
        sa.Column("dim1", sa.String(length=20), nullable=True),
    )
    op.execute("UPDATE health_metrics SET dim1 = 'UNKNOWN' WHERE dim1 IS NULL")
    op.alter_column("health_metrics", "dim1", nullable=False)

    op.drop_constraint(
        "health_metrics_country_code_indicator_year_key",
        "health_metrics",
        type_="unique",
    )
    op.create_unique_constraint(
        "health_metrics_country_code_indicator_year_dim1_key",
        "health_metrics",
        ["country_code", "indicator", "year", "dim1"],
    )
    op.create_index(op.f("ix_health_metrics_dim1"), "health_metrics", ["dim1"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_health_metrics_dim1"), table_name="health_metrics")
    op.drop_constraint(
        "health_metrics_country_code_indicator_year_dim1_key",
        "health_metrics",
        type_="unique",
    )
    op.create_unique_constraint(
        "health_metrics_country_code_indicator_year_key",
        "health_metrics",
        ["country_code", "indicator", "year"],
    )
    op.drop_column("health_metrics", "dim1")
