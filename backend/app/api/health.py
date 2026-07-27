from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import DatabaseSession

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "error"]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe: the application process is running.

    Does not check the database; use ``/ready`` for dependency readiness.
    """
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def ready(session: DatabaseSession) -> JSONResponse:
    """Readiness probe: the application can reach the database.

    Returns 200 when ``SELECT 1`` succeeds and 503 when the database is
    unreachable, so a load balancer can withhold traffic until the backend is
    actually able to serve requests.
    """
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        not_ready = ReadinessResponse(status="not_ready", database="error")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=not_ready.model_dump(),
        )
    ready_payload = ReadinessResponse(status="ready", database="ok")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ready_payload.model_dump(),
    )
