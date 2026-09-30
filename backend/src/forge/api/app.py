"""FastAPI application factory and local service entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forge import __version__
from forge.adapters.sqlite.database import Database, run_migrations
from forge.api.dependencies import SessionDependency
from forge.api.routes.agents import router as agents_router
from forge.api.routes.runs import router as runs_router
from forge.api.schemas import ErrorResponse, HealthResponse
from forge.application.errors import ResourceNotFoundError
from forge.config import Settings
from forge.domain.runs import InvalidRunTransition
from forge.runtime.supervisor import RunSupervisor


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application, allowing temporary settings in tests."""

    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app_settings.resolved_data_dir.mkdir(parents=True, exist_ok=True)
        run_migrations(app_settings.resolved_database_url)
        database = Database(app_settings.resolved_database_url)
        database.ping()
        app.state.database = database
        app.state.settings = app_settings
        supervisor = RunSupervisor(database, app_settings)
        supervisor.recover()
        app.state.supervisor = supervisor
        try:
            yield
        finally:
            await supervisor.close()
            database.close()

    application = FastAPI(
        title="Forge API",
        description="The local runtime API for Forge agents.",
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def assign_request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(ResourceNotFoundError)
    async def resource_not_found(
        request: Request, error: ResourceNotFoundError
    ) -> JSONResponse:
        body = ErrorResponse(
            detail=str(error),
            request_id=request.state.request_id,
            resource=error.resource,
            resource_id=error.resource_id,
        )
        return JSONResponse(status_code=404, content=body.model_dump())

    @application.exception_handler(Exception)
    async def internal_error(request: Request, _: Exception) -> JSONResponse:
        request_id = request.state.request_id
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    @application.exception_handler(InvalidRunTransition)
    async def invalid_run_transition(
        request: Request, error: InvalidRunTransition
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": str(error), "request_id": request.state.request_id},
        )

    @application.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "service": "forge-api",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @application.get(
        "/api/v1/health", response_model=HealthResponse, tags=["system"]
    )
    def health(session: SessionDependency) -> HealthResponse:
        session.connection().exec_driver_sql("SELECT 1")
        return HealthResponse(
            status="ok",
            service="forge-api",
            version=__version__,
            database="ready",
        )

    application.include_router(agents_router, prefix="/api/v1")
    application.include_router(runs_router, prefix="/api/v1")
    return application


app = create_app()


def run() -> None:
    """Run the local development service through the project script."""

    import uvicorn

    uvicorn.run("forge.api.app:app", host="127.0.0.1", port=8000, reload=True)
