from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

OrganizationType = Literal["HOSPITAL", "CLINIC", "DIAGNOSTIC_CENTER", "BLOOD_BANK", "OTHER"]
VerificationStatus = Literal["PENDING", "VERIFIED", "REJECTED"]


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    registration_number: str = Field(..., min_length=1, max_length=128)
    organization_type: OrganizationType
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=16)

    @field_validator("name", "address", "city", "state", "registration_number")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("registration_number")
    @classmethod
    def normalize_registration_number(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.isdigit() or len(normalized) < 4 or len(normalized) > 10:
            raise ValueError("pincode must contain 4 to 10 digits")
        return normalized


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    registration_number: str | None = Field(default=None, min_length=1, max_length=128)
    organization_type: OrganizationType | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=16)

    @field_validator("name", "address", "city", "state", "registration_number")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("registration_number")
    @classmethod
    def normalize_registration_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.isdigit() or len(normalized) < 4 or len(normalized) > 10:
            raise ValueError("pincode must contain 4 to 10 digits")
        return normalized


class OrganizationVerificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_status: Literal["VERIFIED", "REJECTED"]


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    registration_number: str
    organization_type: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    verification_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationMemberAssociation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
