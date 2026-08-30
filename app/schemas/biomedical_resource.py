from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResourceCategory = Literal["EQUIPMENT", "MEDICINE", "BLOOD", "MEDICAL_SUPPLY", "OTHER"]
AvailabilityStatus = Literal["AVAILABLE", "LOW_STOCK", "OUT_OF_STOCK", "UNAVAILABLE"]
ResourceCondition = Literal["NEW", "GOOD", "USED", "DAMAGED"]


class BiomedicalResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    category: ResourceCategory
    description: str | None = Field(default=None, max_length=2000)
    quantity: int = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=64)
    availability_status: AvailabilityStatus = "AVAILABLE"
    condition: ResourceCondition = "NEW"
    expiry_date: datetime | None = None

    @field_validator("name", "unit")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class BiomedicalResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: ResourceCategory | None = None
    description: str | None = Field(default=None, max_length=2000)
    quantity: int | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    availability_status: AvailabilityStatus | None = None
    condition: ResourceCondition | None = None
    expiry_date: datetime | None = None
    is_active: bool | None = None

    @field_validator("name", "unit")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class BiomedicalResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    name: str
    category: str
    description: str | None = None
    quantity: int
    unit: str
    availability_status: str
    condition: str
    expiry_date: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
