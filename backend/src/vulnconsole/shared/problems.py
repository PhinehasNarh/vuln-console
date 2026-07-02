"""RFC 9457 problem details: application error type and FastAPI handlers."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://vulnconsole.dev/problems"


class ProblemError(Exception):
    def __init__(
        self,
        *,
        status: int,
        title: str,
        detail: str,
        slug: str = "error",
        errors: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.slug = slug
        self.errors = errors
        self.headers = headers


def _problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    slug: str,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}/{slug}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(
        status_code=status, content=body, media_type=PROBLEM_CONTENT_TYPE, headers=headers
    )


def register_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return _problem_response(
            request,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
            slug=exc.slug,
            errors=exc.errors,
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem_response(
            request,
            status=exc.status_code,
            title="Request failed",
            detail=str(exc.detail),
            slug="http-error",
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())),
                "message": str(err.get("msg", "invalid")),
            }
            for err in exc.errors()
        ]
        return _problem_response(
            request,
            status=422,
            title="Validation failed",
            detail=f"{len(errors)} field(s) failed validation",
            slug="validation-error",
            errors=errors,
        )
