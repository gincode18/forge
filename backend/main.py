"""The local HTTP entry point for the Forge runtime."""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """A stable readiness contract for local clients."""

    status: Literal["ok"]
    service: str
    version: str


app = FastAPI(
    title="Forge API",
    description="The local runtime API for Forge agents.",
    version="0.1.0",
)

# The dashboard is a separate local development server. Keep this deliberately
# narrow until Forge gains configurable deployment settings.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Identify the service and point developers to the versioned API."""

    return {"service": "forge-api", "docs": "/docs", "health": "/api/v1/health"}


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return a lightweight readiness response for the Forge dashboard."""

    return HealthResponse(status="ok", service="forge-api", version=app.version)
