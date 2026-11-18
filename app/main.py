"""Application entry point: `uvicorn app.main:app`."""

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import RequestLoggingMiddleware, setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "error_code": exc.error_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        error_msgs = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"] if part != "body")
            error_msgs.append(f"{loc}: {err['msg']}" if loc else err["msg"])
        message = "; ".join(error_msgs) if error_msgs else "Validation error"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": message, "error_code": "VALIDATION_ERROR"},
        )

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/docs")

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    def web_ui():
        ui_path = Path(__file__).resolve().parent / "static" / "index.html"
        if ui_path.exists():
            return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>LedgerForge UI</h1><p><a href='/docs'>Swagger API Docs</a></p>")

    # Primary versioned API routes (/api/v1)
    app.include_router(api_router, prefix="/api/v1")
    # Legacy alias router for backwards compatibility
    app.include_router(api_router, include_in_schema=False)
    return app


app = create_app()
