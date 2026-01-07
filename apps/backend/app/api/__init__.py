"""API routes package."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.detection import router as detection_router
from app.api.documents import router as documents_router
from app.api.envelopes import router as envelopes_router
from app.api.fields import router as fields_router
from app.api.signing import router as signing_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(fields_router)
api_router.include_router(detection_router)
api_router.include_router(envelopes_router)
api_router.include_router(signing_router)
