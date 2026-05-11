from fastapi import APIRouter

from app.assets.router import router as assets_router
from app.auth.router import router as auth_router
from app.health.router import router as health_router
from app.upload.router import router as upload_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(upload_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])

