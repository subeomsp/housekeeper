from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError


def error_content(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def handle_app_error(_request: Request, exception: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            content=jsonable_encoder(
                error_content(exception.code, exception.message, exception.details)
            ),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                error_content(
                    "VALIDATION_ERROR",
                    "요청 값이 올바르지 않습니다.",
                    {"errors": exception.errors()},
                )
            ),
        )

    @application.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        _request: Request,
        _exception: SQLAlchemyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_content(
                "DATABASE_ERROR",
                "데이터베이스 처리 중 오류가 발생했습니다.",
                {},
            ),
        )
