"""Retain verified WordPress publication dates for article age comparisons."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column(
        "publications",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("publications", "published_at")
