from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ResourceCategory = Literal["EQUIPMENT", "MEDICINE", "BLOOD", "MEDICAL_SUPPLY", "OTHER"]
AvailabilityStatus = Literal["AVAILABLE", "LOW_STOCK", "OUT_OF_STOCK", "UNAVAILABLE"]


class ResourceDiscoveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    category: str
    description: str | None = None
    quantity: int
    unit: str
    availability_status: str
    condition: str
    expiry_date: datetime | None = None
    provider_organization_id: int
    provider_organization_name: str
    provider_organization_type: str
    provider_city: str | None = None
    provider_state: str | None = None
