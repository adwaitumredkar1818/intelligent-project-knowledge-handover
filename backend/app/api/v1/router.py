"""Central router registry for `/api/v1` endpoints."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.health import v1_health_router
from app.api.routes.organisations import router as organisations_router
from app.api.routes.projects import router as projects_router
from app.api.routes.sources import router as sources_router
from app.api.routes.users import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(v1_health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(organisations_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(evidence_router)
