from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.resource_request import ResourceRequest


class ResourceCategory(str, Enum):
    EQUIPMENT = "EQUIPMENT"
    MEDICINE = "MEDICINE"
    BLOOD = "BLOOD"
    MEDICAL_SUPPLY = "MEDICAL_SUPPLY"
    OTHER = "OTHER"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNAVAILABLE = "UNAVAILABLE"


class ResourceCondition(str, Enum):
    NEW = "NEW"
    GOOD = "GOOD"
    USED = "USED"
    DAMAGED = "DAMAGED"


class BiomedicalResource(Base):
    __tablename__ = "biomedical_resources"
    __table_args__ = (
        Index("ix_biomedical_resources_organization_id", "organization_id"),
        Index("ix_biomedical_resources_category", "category"),
        Index("ix_biomedical_resources_availability_status", "availability_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ResourceCategory.EQUIPMENT.value,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    availability_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE.value,
        index=True,
    )
    condition: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ResourceCondition.NEW.value,
    )
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship(back_populates="biomedical_resources")
    requests: Mapped[list["ResourceRequest"]] = relationship(back_populates="resource")

    @validates("quantity")
    def validate_quantity(self, key: str, value: int) -> int:
        if value < 0:
            raise ValueError("quantity cannot be negative")
        return value
