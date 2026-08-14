"""Compatibility entry point for ``uv run fastapi dev main.py``."""

from forge.api.app import app

__all__ = ["app"]
