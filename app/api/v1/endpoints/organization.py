from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import CurrentUser
from app.db.session import get_db
from app.models import Organization, User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationMemberAssociation,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationVerificationUpdate,
)

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


def _get_organization_or_404(db: Session, organization_id: int) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


def _require_same_or_admin(current_user: User, organization: Organization) -> None:
    if current_user.role == "admin":
        return
    if current_user.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization",
        )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Organization:
    if current_user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already associated with an organization",
        )

    organization = Organization(
        name=payload.name,
        registration_number=payload.registration_number,
        organization_type=payload.organization_type,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        verification_status="PENDING",
        is_active=True,
    )
    db.add(organization)
    try:
        db.flush()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization registration number already exists",
        ) from None

    current_user.organization_id = organization.id
    db.commit()
    db.refresh(organization)
    return organization


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(current_user: CurrentUser, db: DatabaseSession) -> Organization:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with any organization",
        )

    organization = _get_organization_or_404(db, current_user.organization_id)
    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Organization:
    organization = _get_organization_or_404(db, organization_id)
    _require_same_or_admin(current_user, organization)
    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Organization:
    organization = _get_organization_or_404(db, organization_id)
    _require_same_or_admin(current_user, organization)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    organization.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(organization)
    return organization


@router.patch("/{organization_id}/verify", response_model=OrganizationResponse)
def verify_organization(
    organization_id: int,
    payload: OrganizationVerificationUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Organization:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can verify or reject organizations",
        )

    organization = _get_organization_or_404(db, organization_id)
    if organization.verification_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only organizations in PENDING state can be verified or rejected",
        )

    organization.verification_status = payload.verification_status
    organization.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/{organization_id}/members", response_model=OrganizationResponse)
def add_organization_member(
    organization_id: int,
    payload: OrganizationMemberAssociation,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Organization:
    organization = _get_organization_or_404(db, organization_id)
    if current_user.role != "admin" and current_user.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage organization membership",
        )

    target_user = db.scalar(select(User).where(User.id == payload.user_id))
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if target_user.organization_id is not None and target_user.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already belongs to another organization",
        )

    target_user.organization_id = organization.id
    db.commit()
    return organization
