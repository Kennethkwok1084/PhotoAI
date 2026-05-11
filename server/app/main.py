from fastapi import FastAPI
from fastapi import Request

from app.api.router import api_router
from app.common.responses import ok
from app.common.errors import register_exception_handlers
from app.common.middleware import RequestIdMiddleware
from app.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get("/")
    def root(request: Request):
        return ok(
            request,
            {
                "service": settings.app_name,
                "version": "0.1.0",
                "status": "running",
                "api_base": "/api",
                "health_url": "/api/health",
                "docs_url": "/docs",
            },
        )

    @app.get("/api")
    def api_root(request: Request):
        return ok(
            request,
            {
                "service": settings.app_name,
                "version": "0.1.0",
                "health_url": "/api/health",
                "auth_url": "/api/auth",
                "assets_url": "/api/assets",
                "uploads_url": "/api/uploads",
            },
        )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

