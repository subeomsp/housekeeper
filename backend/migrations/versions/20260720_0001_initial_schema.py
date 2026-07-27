"""Create Phase 1 inventory schema.

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_households")),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "household_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_household_members_household_id_households"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_household_members_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_household_members")),
        sa.UniqueConstraint("household_id", "user_id", name="uq_household_member"),
    )
    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("default_unit", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
            ["household_id"],
            ["households.id"],
            name=op.f("fk_inventory_items_household_id_households"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_items")),
        sa.UniqueConstraint(
            "household_id",
            "normalized_name",
            name="uq_inventory_item_name",
        ),
    )
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=12, scale=3),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_inventory_quantity_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_inventory_household_id_households"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["inventory_items.id"],
            name=op.f("fk_inventory_item_id_inventory_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory")),
        sa.UniqueConstraint("household_id", "item_id", name="uq_inventory_item"),
    )
    op.create_table(
        "inventory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column(
            "signed_quantity",
            sa.Numeric(precision=12, scale=3),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source",
            sa.String(length=30),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversal_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_event_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_inventory_events_created_by_users"),
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_inventory_events_household_id_households"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["inventory_items.id"],
            name=op.f("fk_inventory_events_item_id_inventory_items"),
        ),
        sa.ForeignKeyConstraint(
            ["reversal_event_id"],
            ["inventory_events.id"],
            name=op.f("fk_inventory_events_reversal_event_id_inventory_events"),
        ),
        sa.ForeignKeyConstraint(
            ["reversed_by"],
            ["users.id"],
            name=op.f("fk_inventory_events_reversed_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_events")),
    )


def downgrade() -> None:
    op.drop_table("inventory_events")
    op.drop_table("inventory")
    op.drop_table("inventory_items")
    op.drop_table("household_members")
    op.drop_table("users")
    op.drop_table("households")

