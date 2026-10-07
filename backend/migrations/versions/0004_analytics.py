"""Daily observations and import provenance, separate from period summaries."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"


def upgrade():
    for name in ("analytics_rows", "analytics_batches"):
        columns = [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("property", sa.Text(), nullable=False),
            sa.Column("dataset", sa.String(20), nullable=False),
        ]
        if name == "analytics_rows":
            columns += [
                sa.Column("day", sa.String(10), nullable=False),
                sa.Column("dimensions", JSONB(), nullable=False),
                sa.Column("values", JSONB(), nullable=False),
                sa.Column("quality", sa.String(40), nullable=False),
                sa.UniqueConstraint(
                    "provider", "property", "dataset", "day", "dimensions"
                ),
            ]
        else:
            columns += [
                sa.Column("start", sa.String(10), nullable=False),
                sa.Column("end", sa.String(10), nullable=False),
                sa.Column("metadata", JSONB(), nullable=False),
                sa.Column("rows", sa.Integer(), nullable=False),
            ]
        op.create_table(name, *columns)
    op.create_index("ix_analytics_rows_day", "analytics_rows", ["day"])


def downgrade():
    op.drop_table("analytics_rows")
    op.drop_table("analytics_batches")
