from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies import CurrentUser
from app.db.session import get_db
from app.models import (
    BiomedicalResource,
    Organization,
    ResourceRequest,
    ResourceRequestStatus,
    User,
)
from app.models.biomedical_resource import AvailabilityStatus
from app.schemas.biomedical_resource import AvailabilityStatus as AvailabilityStatusLiteral
from app.schemas.biomedical_resource import ResourceCategory
from app.schemas.resource_discovery import ResourceDiscoveryResponse
from app.schemas.resource_request import ResourceRequestCreate, ResourceRequestResponse

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


def _require_verified_organization(current_user: User) -> Organization:
    organization = current_user.organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )
    if not organization.is_active or organization.verification_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active and verified for resource sharing",
        )
    return organization


def _request_to_response(resource_request: ResourceRequest) -> ResourceRequestResponse:
    return ResourceRequestResponse(
        id=resource_request.id,
        resource_id=resource_request.resource_id,
        resource_name=resource_request.resource.name,
        requesting_organization_id=resource_request.requesting_organization_id,
        requesting_organization_name=resource_request.requesting_organization.name,
        providing_organization_id=resource_request.providing_organization_id,
        providing_organization_name=resource_request.providing_organization.name,
        requested_quantity=resource_request.requested_quantity,
        message=resource_request.message,
        status=resource_request.status,
        created_at=resource_request.created_at,
        updated_at=resource_request.updated_at,
    )


def _get_visible_request(
    db: Session,
    request_id: int,
    organization_id: int,
) -> ResourceRequest:
    resource_request = db.scalar(
        select(ResourceRequest)
        .options(
            joinedload(ResourceRequest.resource),
            joinedload(ResourceRequest.requesting_organization),
            joinedload(ResourceRequest.providing_organization),
        )
        .where(
            ResourceRequest.id == request_id,
            or_(
                ResourceRequest.requesting_organization_id == organization_id,
                ResourceRequest.providing_organization_id == organization_id,
            ),
        )
    )
    if resource_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource request not found",
        )
    return resource_request


def _require_pending(resource_request: ResourceRequest) -> None:
    _require_status(resource_request, ResourceRequestStatus.PENDING)


def _require_status(resource_request: ResourceRequest, expected_status: ResourceRequestStatus) -> None:
    if resource_request.status != expected_status.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {expected_status.value.lower()} resource requests can change status",
        )


def _load_resource_for_request(db: Session, resource_id: int) -> BiomedicalResource:
    resource = db.scalar(
        select(BiomedicalResource)
        .options(joinedload(BiomedicalResource.organization))
        .where(BiomedicalResource.id == resource_id)
    )
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return resource


@router.get(
    "/resource-sharing/resources",
    response_model=list[ResourceDiscoveryResponse],
)
def discover_resources(
    current_user: CurrentUser,
    db: DatabaseSession,
    category: ResourceCategory | None = Query(default=None),
    availability_status: AvailabilityStatusLiteral | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
) -> list[ResourceDiscoveryResponse]:
    organization = _require_verified_organization(current_user)
    allowed_availability = [
        AvailabilityStatus.AVAILABLE.value,
        AvailabilityStatus.LOW_STOCK.value,
    ]
    stmt = (
        select(BiomedicalResource, Organization)
        .join(Organization, BiomedicalResource.organization_id == Organization.id)
        .where(
            BiomedicalResource.organization_id != organization.id,
            BiomedicalResource.is_active.is_(True),
            BiomedicalResource.quantity > 0,
            BiomedicalResource.availability_status.in_(allowed_availability),
            Organization.is_active.is_(True),
            Organization.verification_status == "VERIFIED",
        )
        .order_by(BiomedicalResource.updated_at.desc())
    )
    if category is not None:
        stmt = stmt.where(BiomedicalResource.category == category)
    if availability_status is not None:
        stmt = stmt.where(BiomedicalResource.availability_status == availability_status)
    if search is not None and search.strip():
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                BiomedicalResource.name.ilike(search_pattern),
                BiomedicalResource.description.ilike(search_pattern),
            )
        )

    return [
        ResourceDiscoveryResponse(
            id=resource.id,
            name=resource.name,
            category=resource.category,
            description=resource.description,
            quantity=resource.quantity,
            unit=resource.unit,
            availability_status=resource.availability_status,
            condition=resource.condition,
            expiry_date=resource.expiry_date,
            provider_organization_id=provider.id,
            provider_organization_name=provider.name,
            provider_organization_type=provider.organization_type,
            provider_city=provider.city,
            provider_state=provider.state,
        )
        for resource, provider in db.execute(stmt).all()
    ]


@router.post(
    "/resource-requests",
    response_model=ResourceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource_request(
    payload: ResourceRequestCreate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    requesting_organization = _require_verified_organization(current_user)
    resource = _load_resource_for_request(db, payload.resource_id)
    providing_organization = resource.organization

    if resource.organization_id == requesting_organization.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request a resource from your own organization",
        )
    if not providing_organization.is_active or providing_organization.verification_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource provider is not active and verified",
        )
    if not resource.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource is not active",
        )
    if resource.quantity <= 0 or resource.availability_status not in {
        AvailabilityStatus.AVAILABLE.value,
        AvailabilityStatus.LOW_STOCK.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource is not currently available for requests",
        )
    if payload.requested_quantity > resource.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available quantity",
        )

    resource_request = ResourceRequest(
        resource_id=resource.id,
        requesting_organization_id=requesting_organization.id,
        providing_organization_id=providing_organization.id,
        requesting_user_id=current_user.id,
        requested_quantity=payload.requested_quantity,
        message=payload.message,
        status=ResourceRequestStatus.PENDING.value,
    )
    db.add(resource_request)
    db.commit()
    db.refresh(resource_request)
    resource_request.resource = resource
    resource_request.requesting_organization = requesting_organization
    resource_request.providing_organization = providing_organization
    return _request_to_response(resource_request)


@router.get(
    "/resource-requests",
    response_model=list[ResourceRequestResponse],
)
def list_resource_requests(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> list[ResourceRequestResponse]:
    organization = _require_verified_organization(current_user)
    requests = db.scalars(
        select(ResourceRequest)
        .options(
            joinedload(ResourceRequest.resource),
            joinedload(ResourceRequest.requesting_organization),
            joinedload(ResourceRequest.providing_organization),
        )
        .where(
            or_(
                ResourceRequest.requesting_organization_id == organization.id,
                ResourceRequest.providing_organization_id == organization.id,
            )
        )
        .order_by(ResourceRequest.created_at.desc())
    ).all()
    return [_request_to_response(resource_request) for resource_request in requests]


@router.get(
    "/resource-requests/{request_id}",
    response_model=ResourceRequestResponse,
)
def get_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    return _request_to_response(resource_request)


@router.post(
    "/resource-requests/{request_id}/approve",
    response_model=ResourceRequestResponse,
)
def approve_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    if resource_request.providing_organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the providing organization can approve this request",
        )
    _require_pending(resource_request)
    resource = _load_resource_for_request(db, resource_request.resource_id)
    if not resource.is_active or resource.quantity <= 0 or resource.quantity < resource_request.requested_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource is no longer available for this request",
        )

    resource_request.status = ResourceRequestStatus.APPROVED.value
    resource_request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource_request)
    return _request_to_response(resource_request)


@router.post(
    "/resource-requests/{request_id}/reject",
    response_model=ResourceRequestResponse,
)
def reject_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    if resource_request.providing_organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the providing organization can reject this request",
        )
    _require_pending(resource_request)
    resource_request.status = ResourceRequestStatus.REJECTED.value
    resource_request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource_request)
    return _request_to_response(resource_request)


@router.post(
    "/resource-requests/{request_id}/cancel",
    response_model=ResourceRequestResponse,
)
def cancel_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    if resource_request.requesting_organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requesting organization can cancel this request",
        )
    _require_pending(resource_request)
    resource_request.status = ResourceRequestStatus.CANCELLED.value
    resource_request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource_request)
    return _request_to_response(resource_request)


@router.post(
    "/resource-requests/{request_id}/fulfill",
    response_model=ResourceRequestResponse,
)
def fulfill_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    if resource_request.providing_organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the providing organization can fulfill this request",
        )
    _require_status(resource_request, ResourceRequestStatus.APPROVED)

    resource = _load_resource_for_request(db, resource_request.resource_id)
    if not resource.organization.is_active or resource.organization.verification_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource provider is not active and verified",
        )

    try:
        quantity_update = db.execute(
            update(BiomedicalResource)
            .where(
                BiomedicalResource.id == resource_request.resource_id,
                BiomedicalResource.is_active.is_(True),
                BiomedicalResource.quantity >= resource_request.requested_quantity,
                BiomedicalResource.availability_status.in_(
                    [
                        AvailabilityStatus.AVAILABLE.value,
                        AvailabilityStatus.LOW_STOCK.value,
                    ]
                ),
            )
            .values(
                quantity=BiomedicalResource.quantity - resource_request.requested_quantity,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if quantity_update.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource is no longer available for fulfillment",
            )

        request_update = db.execute(
            update(ResourceRequest)
            .where(
                ResourceRequest.id == request_id,
                ResourceRequest.status == ResourceRequestStatus.APPROVED.value,
            )
            .values(
                status=ResourceRequestStatus.FULFILLED.value,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if request_update.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only approved resource requests can be fulfilled",
            )

        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fulfill resource request",
        ) from None

    db.refresh(resource_request)
    return _request_to_response(resource_request)


@router.post(
    "/resource-requests/{request_id}/receive",
    response_model=ResourceRequestResponse,
)
def receive_resource_request(
    request_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ResourceRequestResponse:
    organization = _require_verified_organization(current_user)
    resource_request = _get_visible_request(db, request_id, organization.id)
    if resource_request.requesting_organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requesting organization can confirm receipt",
        )
    _require_status(resource_request, ResourceRequestStatus.FULFILLED)

    receipt_update = db.execute(
        update(ResourceRequest)
        .where(
            ResourceRequest.id == request_id,
            ResourceRequest.status == ResourceRequestStatus.FULFILLED.value,
        )
        .values(
            status=ResourceRequestStatus.RECEIVED.value,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if receipt_update.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only fulfilled resource requests can be received",
        )

    db.commit()
    db.refresh(resource_request)
    return _request_to_response(resource_request)
