
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_phase2_domain_models"
down_revision: Union[str, None] = "001_phase1_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TYPE_VALUES = (
    "ENTRY",
    "EXIT",
    "ZONE_ENTER",
    "ZONE_EXIT",
    "ZONE_DWELL",
    "BILLING_QUEUE_JOIN",
    "BILLING_QUEUE_ABANDON",
    "PURCHASE",
    "REENTRY",
)


def upgrade() -> None:
    event_type_enum = sa.Enum(*EVENT_TYPE_VALUES, name="event_type_enum")
    event_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_name", sa.String(length=128), nullable=False),
        sa.Column("camera_code", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("camera_code", name="uq_cameras_camera_code"),
    )
    op.create_index("ix_cameras_camera_code", "cameras", ["camera_code"], unique=True)

    op.create_table(
        "visitor_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("converted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_visitor_sessions_visitor_id",
        "visitor_sessions",
        ["visitor_id"],
        unique=False,
    )

    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zone_name", sa.String(length=128), nullable=False),
        sa.Column("zone_type", sa.String(length=64), nullable=False),
        sa.Column("polygon_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("camera_id", "zone_name", name="uq_zones_camera_id_zone_name"),
    )
    op.create_index("ix_zones_camera_id", "zones", ["camera_id"], unique=False)
    op.create_index("ix_zones_zone_type", "zones", ["zone_type"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("basket_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("visitor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["visitor_session_id"],
            ["visitor_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", name="uq_transactions_transaction_id"),
        sa.UniqueConstraint("visitor_session_id", name="uq_transactions_visitor_session_id"),
    )
    op.create_index(
        "ix_transactions_transaction_id",
        "transactions",
        ["transaction_id"],
        unique=True,
    )
    op.create_index(
        "ix_transactions_transaction_timestamp",
        "transactions",
        ["transaction_timestamp"],
        unique=False,
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["visitor_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_visitor_id", "events", ["visitor_id"], unique=False)
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)
    op.create_index("ix_events_timestamp", "events", ["timestamp"], unique=False)
    op.create_index("ix_events_camera_id", "events", ["camera_id"], unique=False)
    op.create_index("ix_events_zone_id", "events", ["zone_id"], unique=False)
    op.create_index("ix_events_session_id", "events", ["session_id"], unique=False)
    op.create_index(
        "ix_events_visitor_id_timestamp",
        "events",
        ["visitor_id", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_events_visitor_id_timestamp", table_name="events")
    op.drop_index("ix_events_session_id", table_name="events")
    op.drop_index("ix_events_zone_id", table_name="events")
    op.drop_index("ix_events_camera_id", table_name="events")
    op.drop_index("ix_events_timestamp", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_visitor_id", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_transactions_transaction_timestamp", table_name="transactions")
    op.drop_index("ix_transactions_transaction_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_zones_zone_type", table_name="zones")
    op.drop_index("ix_zones_camera_id", table_name="zones")
    op.drop_table("zones")

    op.drop_index("ix_visitor_sessions_visitor_id", table_name="visitor_sessions")
    op.drop_table("visitor_sessions")

    op.drop_index("ix_cameras_camera_code", table_name="cameras")
    op.drop_table("cameras")

    event_type_enum = sa.Enum(*EVENT_TYPE_VALUES, name="event_type_enum")
    event_type_enum.drop(op.get_bind(), checkfirst=True)
