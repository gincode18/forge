"""Database engine, sessions, migration, and SQLite configuration."""

from collections.abc import Iterator
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def create_database_engine(database_url: str) -> Engine:
    """Create an engine with safe local SQLite defaults."""

    connect_args = {"check_same_thread": False} if _is_sqlite(database_url) else {}
    engine = create_engine(database_url, connect_args=connect_args)

    if _is_sqlite(database_url):

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def run_migrations(database_url: str) -> None:
    """Upgrade the configured database to the latest schema revision."""

    backend_root = Path(__file__).resolve().parents[4]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


class Database:
    """Own the engine and produce short-lived transaction sessions."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_database_engine(database_url)
        self._sessions = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    def session(self) -> Iterator[Session]:
        with self._sessions() as session:
            yield session

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def close(self) -> None:
        self.engine.dispose()
