from fastapi import FastAPI

from app.api.router import api_router
from app.common.errors import register_exception_handlers
from app.common.middleware import RequestIdMiddleware
from app.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

