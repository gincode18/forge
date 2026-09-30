from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


def test_limits_migration_preserves_historical_versions_both_directions(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    url = f"sqlite:///{tmp_path / 'historical.db'}"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0002")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO agents VALUES ('agent', 'Historical', NULL, '2026-01-01')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO agent_versions VALUES ('version', 'agent', 1, 'Original', 'fake', 'deterministic', 'react', '[]', 12, '2026-01-01')"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT * FROM agent_versions")).mappings().one()
        assert row["instructions"] == "Original"
        assert row["timeout_seconds"] == 30
        assert row["max_retries"] == 2
        assert row["max_output_tokens"] == 2048
        assert row["max_tokens"] is None
        assert row["max_cost_usd"] is None
        assert row["input_cost_per_million"] is None
        assert row["output_cost_per_million"] is None
    command.downgrade(config, "0002")
    assert "timeout_seconds" not in {
        column["name"] for column in inspect(engine).get_columns("agent_versions")
    }
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT instructions FROM agent_versions")
            ).scalar_one()
            == "Original"
        )
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
