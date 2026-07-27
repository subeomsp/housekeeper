from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db_session


class _OkSession:
    async def execute(self, statement: object) -> None:
        return None


class _FailingSession:
    async def execute(self, statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_returns_200_when_database_reachable(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_db_session] = lambda: _OkSession()

    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


async def test_ready_returns_503_when_database_unreachable(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_db_session] = lambda: _FailingSession()

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "error"}
