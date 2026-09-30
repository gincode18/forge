"""Local provider catalog: configuration status, never credentials or discovery."""

import os

from fastapi import APIRouter, Request

from forge.api.schemas import ProviderResponse

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
def get_providers(request: Request) -> list[ProviderResponse]:
    settings = request.app.state.settings
    configured = bool(settings.gemini_api_key) or bool(os.environ.get("GEMINI_API_KEY"))
    return [
        ProviderResponse(id="fake", configured=True, default_model="deterministic"),
        ProviderResponse(
            id="gemini", configured=configured, default_model="gemini-3.5-flash-lite"
        ),
    ]
