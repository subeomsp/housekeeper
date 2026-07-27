from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InventoryEvent(Base):
    __tablename__ = "inventory_events"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_event_quantity_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    household_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("households.id"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("inventory_items.id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    signed_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reversed_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reversal_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("inventory_events.id"),
        nullable=True,
    )

