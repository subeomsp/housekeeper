from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router, prefix=resolved_settings.api_v1_prefix)
    return application


app = create_app()
