from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "normalized_name",
            name="uq_inventory_item_name",
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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

