from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_store_id_is_staff"
down_revision: Union[str, None] = "002_phase2_domain_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add store_id and is_staff to events
    op.add_column(
        "events",
        sa.Column(
            "store_id",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "is_staff",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_events_store_id", "events", ["store_id"], unique=False)

    # Add store_id to visitor_sessions
    op.add_column(
        "visitor_sessions",
        sa.Column(
            "store_id",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.create_index(
        "ix_visitor_sessions_store_id",
        "visitor_sessions",
        ["store_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_visitor_sessions_store_id", table_name="visitor_sessions")
    op.drop_column("visitor_sessions", "store_id")
    op.drop_index("ix_events_store_id", table_name="events")
    op.drop_column("events", "is_staff")
    op.drop_column("events", "store_id")