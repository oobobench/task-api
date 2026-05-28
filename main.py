import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from routes import auth, tasks

logger = logging.getLogger("task_api")

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

app = FastAPI(title="Task Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


def _error_response(
    request: Request,
    status_code: int,
    error: str,
    message: str,
    details=None,
) -> JSONResponse:
    body = {
        "error": error,
        "message": message,
        "status_code": status_code,
        "request_id": getattr(request.state, "request_id", "-"),
    }
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _error_response(
        request,
        status_code=exc.status_code,
        error="http_error",
        message=str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.exception("Database error", extra={"request_id": getattr(request.state, "request_id", "-")})
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="database_error",
        message="A database error occurred",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", extra={"request_id": getattr(request.state, "request_id", "-")})
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_error",
        message="An unexpected error occurred",
    )


app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
def health():
    return {"status": "ok"}
