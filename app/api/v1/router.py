from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.organization import router as organization_router
from app.api.v1.endpoints.resources import router as resource_router
from app.api.v1.endpoints.resource_sharing import router as resource_sharing_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(organization_router, prefix="/organizations", tags=["organizations"])
api_router.include_router(resource_router, prefix="/resources", tags=["resources"])
api_router.include_router(resource_sharing_router, tags=["resource-sharing"])
