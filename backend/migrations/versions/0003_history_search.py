"""Indexed Spanish lexical retrieval before semantic overlap review."""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.execute(
        "CREATE INDEX ideas_search ON ideas USING gin(to_tsvector('spanish', title || ' ' || summary || ' ' || angle || ' ' || topic))"
    )
    op.execute(
        "CREATE INDEX publications_search ON publications USING gin(to_tsvector('spanish', title))"
    )


def downgrade():
    op.drop_index("publications_search", table_name="publications")
    op.drop_index("ideas_search", table_name="ideas")
