"""Add the Phase 3 Action Plan foundation.

Revision ID: 20260728_0003
Revises: 20260720_0002
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0003"
down_revision: str | Sequence[str] | None = "20260720_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "voice_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("audio_path", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="planning",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_voice_requests_household_id_households"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_requests")),
    )
    op.create_index(
        op.f("ix_voice_requests_household_id"),
        "voice_requests",
        ["household_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_requests_status"),
        "voice_requests",
        ["status"],
        unique=False,
    )

    op.create_table(
        "action_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "approved",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "executed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["voice_request_id"],
            ["voice_requests.id"],
            name=op.f("fk_action_plans_voice_request_id_voice_requests"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_plans")),
        sa.UniqueConstraint(
            "voice_request_id",
            name="uq_action_plan_voice_request",
        ),
    )

    op.create_table(
        "item_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "inventory_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("normalized_alias", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_item_aliases_household_id_households"),
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name=op.f("fk_item_aliases_inventory_item_id_inventory_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_aliases")),
        sa.UniqueConstraint(
            "household_id",
            "normalized_alias",
            name="uq_item_alias_household_normalized",
        ),
    )


def downgrade() -> None:
    op.drop_table("item_aliases")
    op.drop_table("action_plans")
    op.drop_index(op.f("ix_voice_requests_status"), table_name="voice_requests")
    op.drop_index(
        op.f("ix_voice_requests_household_id"),
        table_name="voice_requests",
    )
    op.drop_table("voice_requests")
