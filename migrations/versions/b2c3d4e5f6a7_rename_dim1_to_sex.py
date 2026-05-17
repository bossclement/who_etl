"""rename dim1 column to sex

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_health_metrics_dim1", table_name="health_metrics")
    op.drop_constraint(
        "health_metrics_country_code_indicator_year_dim1_key",
        "health_metrics",
        type_="unique",
    )
    op.alter_column("health_metrics", "dim1", new_column_name="sex")
    op.create_unique_constraint(
        "health_metrics_country_code_indicator_year_sex_key",
        "health_metrics",
        ["country_code", "indicator", "year", "sex"],
    )
    op.create_index(op.f("ix_health_metrics_sex"), "health_metrics", ["sex"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_health_metrics_sex"), table_name="health_metrics")
    op.drop_constraint(
        "health_metrics_country_code_indicator_year_sex_key",
        "health_metrics",
        type_="unique",
    )
    op.alter_column("health_metrics", "sex", new_column_name="dim1")
    op.create_unique_constraint(
        "health_metrics_country_code_indicator_year_dim1_key",
        "health_metrics",
        ["country_code", "indicator", "year", "dim1"],
    )
    op.create_index(op.f("ix_health_metrics_dim1"), "health_metrics", ["dim1"], unique=False)
