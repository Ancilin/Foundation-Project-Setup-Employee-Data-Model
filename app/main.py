"""Application entry point: `uvicorn app.main:app`."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)

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

    app.include_router(api_router)
    return app


app = create_app()
