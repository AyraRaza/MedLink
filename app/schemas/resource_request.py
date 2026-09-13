from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.resource_request import ResourceRequestStatus


class ResourceRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: int = Field(..., gt=0)
    requested_quantity: int = Field(..., gt=0)
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ResourceRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    resource_id: int
    resource_name: str
    requesting_organization_id: int
    requesting_organization_name: str
    providing_organization_id: int
    providing_organization_name: str
    requested_quantity: int
    message: str | None = None
    status: ResourceRequestStatus
    created_at: datetime
    updated_at: datetime
