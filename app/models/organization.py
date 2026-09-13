from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.biomedical_resource import BiomedicalResource
    from app.models.resource_request import ResourceRequest
    from app.models.user import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registration_number: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    organization_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="HOSPITAL", server_default="HOSPITAL"
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
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

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    biomedical_resources: Mapped[list["BiomedicalResource"]] = relationship(
        back_populates="organization"
    )
    outgoing_resource_requests: Mapped[list["ResourceRequest"]] = relationship(
        foreign_keys="ResourceRequest.requesting_organization_id",
        back_populates="requesting_organization",
    )
    incoming_resource_requests: Mapped[list["ResourceRequest"]] = relationship(
        foreign_keys="ResourceRequest.providing_organization_id",
        back_populates="providing_organization",
    )
