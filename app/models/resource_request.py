from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.biomedical_resource import BiomedicalResource
    from app.models.organization import Organization
    from app.models.user import User


class ResourceRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FULFILLED = "FULFILLED"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ResourceRequest(Base):
    __tablename__ = "resource_requests"
    __table_args__ = (
        Index("ix_resource_requests_resource_id", "resource_id"),
        Index("ix_resource_requests_requesting_organization_id", "requesting_organization_id"),
        Index("ix_resource_requests_providing_organization_id", "providing_organization_id"),
        Index("ix_resource_requests_requesting_user_id", "requesting_user_id"),
        Index("ix_resource_requests_status", "status"),
        Index("ix_resource_requests_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("biomedical_resources.id"), nullable=False
    )
    requesting_organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    providing_organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    requesting_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ResourceRequestStatus.PENDING.value,
        server_default=ResourceRequestStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    resource: Mapped["BiomedicalResource"] = relationship(back_populates="requests")
    requesting_organization: Mapped["Organization"] = relationship(
        foreign_keys=[requesting_organization_id],
        back_populates="outgoing_resource_requests",
    )
    providing_organization: Mapped["Organization"] = relationship(
        foreign_keys=[providing_organization_id],
        back_populates="incoming_resource_requests",
    )
    requesting_user: Mapped["User"] = relationship(back_populates="resource_requests")
