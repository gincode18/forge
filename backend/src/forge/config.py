"""Application configuration for the local Forge service."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from ``FORGE_*`` environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FORGE_",
        env_file=".env",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("data"))
    database_url: str | None = None
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    @property
    def resolved_data_dir(self) -> Path:
        """Return the absolute directory used for local Forge state."""

        return self.data_dir.expanduser().resolve()

    @property
    def resolved_database_url(self) -> str:
        """Return an explicit URL or the SQLite URL inside ``data_dir``."""

        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.resolved_data_dir / 'forge.db'}"
