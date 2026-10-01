from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


@pytest.mark.parametrize('resolved', [False, True])
def test_downgrade_refuses_live_approval_checkpoint_without_losing_diagnostics(client, resolved):
    from test_tools_phase_four import launch, wait

    from forge.application.approvals import resolve_approval

    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    if resolved:
        resolve_approval(client.app.state.database, approval['id'], True)
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    engine = client.app.state.database.engine
    config.set_main_option('sqlalchemy.url', str(engine.url))
    before_events = client.get(f'/api/v1/runs/{run_id}/events').json()
    before_approvals = client.get(f'/api/v1/runs/{run_id}/approvals').json()
    with engine.connect() as connection:
        checkpoint = connection.execute(text('SELECT payload FROM run_checkpoints')).scalar_one()
    with pytest.raises(RuntimeError, match='Cannot downgrade.*approval'):
        command.downgrade(config, '0003')
    assert {'approvals', 'artifacts', 'run_checkpoints'}.issubset(inspect(engine).get_table_names())
    assert client.get(f'/api/v1/runs/{run_id}').json()['status'] == ('running' if resolved else 'waiting_for_approval')
    assert client.get(f'/api/v1/runs/{run_id}/events').json() == before_events
    assert client.get(f'/api/v1/runs/{run_id}/approvals').json() == before_approvals
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0004'
        assert connection.execute(text('SELECT payload FROM run_checkpoints')).scalar_one() == checkpoint
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []


def test_controlled_tools_migration_roundtrip_preserves_historical_trace(tmp_path):
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config.set_main_option('sqlalchemy.url', url)
    command.upgrade(config, '0003')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO agents (id,name,created_at) VALUES ('a','old','2026-01-01')"))
        connection.execute(text("INSERT INTO agent_versions (id,agent_id,version,instructions,provider,model,planner,tools,max_steps,created_at) VALUES ('v','a',1,'old','fake','deterministic','react','[]',12,'2026-01-01')"))
        connection.execute(text("INSERT INTO runs (id,agent_version_id,input,status,created_at,updated_at) VALUES ('r','v','old','completed','2026-01-01','2026-01-01')"))
        connection.execute(text("INSERT INTO events (id,run_id,sequence,type,payload,schema_version,created_at) VALUES ('e','r',1,'run.completed','{}',1,'2026-01-01')"))
    command.upgrade(config, 'head')
    assert {'approvals', 'artifacts', 'run_checkpoints'}.issubset(inspect(engine).get_table_names())
    command.downgrade(config, '0003')
    assert not {'approvals', 'artifacts', 'run_checkpoints'}.intersection(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text('SELECT type FROM events')).scalar_one() == 'run.completed'
        assert connection.execute(text('SELECT instructions FROM agent_versions')).scalar_one() == 'old'
    command.downgrade(config, '0002')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT agent_version_id FROM runs')).scalar_one() == 'v'
        assert connection.execute(text('SELECT instructions FROM agent_versions')).scalar_one() == 'old'
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
    command.upgrade(config, 'head')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT timeout_seconds FROM agent_versions')).scalar_one() == 30
    command.downgrade(config, 'base')
    assert inspect(engine).get_table_names() == ['alembic_version']
    engine.dispose()
