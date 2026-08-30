from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import CurrentUser
from app.db.session import get_db
from app.models import BiomedicalResource, Organization, User
from app.schemas.biomedical_resource import (
    AvailabilityStatus,
    BiomedicalResourceCreate,
    BiomedicalResourceResponse,
    BiomedicalResourceUpdate,
    ResourceCategory,
)

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


def _require_org_membership(current_user: User) -> Organization:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )

    organization = current_user.organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User organization not found",
        )
    return organization


def _get_resource_or_404(db: Session, resource_id: int) -> BiomedicalResource:
    resource = db.get(BiomedicalResource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return resource


def _require_same_organization(current_user: User, resource: BiomedicalResource) -> None:
    if resource.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource",
        )


@router.post("", response_model=BiomedicalResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: BiomedicalResourceCreate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> BiomedicalResource:
    _require_org_membership(current_user)

    resource = BiomedicalResource(
        organization_id=current_user.organization_id,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit,
        availability_status=payload.availability_status,
        condition=payload.condition,
        expiry_date=payload.expiry_date,
        is_active=True,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("", response_model=list[BiomedicalResourceResponse])
def list_resources(
    current_user: CurrentUser,
    db: DatabaseSession,
    category: ResourceCategory | None = Query(default=None),
    availability_status: AvailabilityStatus | None = Query(default=None),
) -> list[BiomedicalResource]:
    _require_org_membership(current_user)

    stmt = select(BiomedicalResource).where(
        BiomedicalResource.organization_id == current_user.organization_id,
        BiomedicalResource.is_active.is_(True),
    )
    if category is not None:
        stmt = stmt.where(BiomedicalResource.category == category)
    if availability_status is not None:
        stmt = stmt.where(BiomedicalResource.availability_status == availability_status)

    resources = db.scalars(stmt).all()
    return resources


@router.get("/{resource_id}", response_model=BiomedicalResourceResponse)
def get_resource(
    resource_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> BiomedicalResource:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )

    resource = _get_resource_or_404(db, resource_id)
    _require_same_organization(current_user, resource)
    return resource


@router.patch("/{resource_id}", response_model=BiomedicalResourceResponse)
def update_resource(
    resource_id: int,
    payload: BiomedicalResourceUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> BiomedicalResource:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )

    resource = _get_resource_or_404(db, resource_id)
    _require_same_organization(current_user, resource)

    update_data = payload.model_dump(exclude_unset=True)
    if "organization_id" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id cannot be changed",
        )

    for field, value in update_data.items():
        setattr(resource, field, value)

    resource.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/{resource_id}", response_model=BiomedicalResourceResponse)
def deactivate_resource(
    resource_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> BiomedicalResource:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )

    resource = _get_resource_or_404(db, resource_id)
    _require_same_organization(current_user, resource)

    resource.is_active = False
    resource.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource)
    return resource
