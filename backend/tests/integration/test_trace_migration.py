"""Trace migration leaves legacy identities unknown and preserves all rows."""
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


@pytest.mark.parametrize('resolved', [False, True])
def test_trace_downgrade_preflights_live_approval_before_removing_columns(client, resolved):
    from test_tools_phase_four import launch, wait

    from forge.application.approvals import resolve_approval

    run_id = launch(client, ['filesystem_write@1'], '{"forge_script":[{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"4"}}]}')
    wait(client, run_id, 'waiting_for_approval')
    approval = client.get(f'/api/v1/runs/{run_id}/approvals').json()[0]
    if resolved:
        resolve_approval(client.app.state.database, approval['id'], True)
    before = client.get(f'/api/v1/runs/{run_id}/events').json()
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    engine = client.app.state.database.engine
    config.set_main_option('sqlalchemy.url', str(engine.url))
    with pytest.raises(RuntimeError, match='Cannot downgrade.*approval'):
        command.downgrade(config, '0003')
    assert 'trace_id' in {c['name'] for c in inspect(engine).get_columns('events')}
    assert client.get(f'/api/v1/runs/{run_id}/events').json() == before
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0005'
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []


def test_trace_migration_upgrade_downgrade_preserves_rows(tmp_path):
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    url = f"sqlite:///{tmp_path / 'trace.db'}"
    config.set_main_option('sqlalchemy.url', url)
    command.upgrade(config, '0004')
    engine = create_engine(url)
    with engine.begin() as connection:
        for sql in [
            "INSERT INTO agents (id,name,created_at) VALUES ('a','old','2026-01-01')",
            "INSERT INTO agent_versions (id,agent_id,version,instructions,provider,model,planner,tools,max_steps,created_at) VALUES ('v','a',1,'old','fake','deterministic','react','[]',12,'2026-01-01')",
            "INSERT INTO runs (id,agent_version_id,input,status,created_at,updated_at) VALUES ('r','v','old','completed','2026-01-01','2026-01-01')",
            "INSERT INTO steps (id,run_id,sequence,kind,status,input,attempt,created_at) VALUES ('s','r',1,'model','completed','{}',1,'2026-01-01')",
            "INSERT INTO events (id,run_id,sequence,type,payload,schema_version,created_at) VALUES ('e','r',1,'model.completed','{\"step_id\":\"s\"}',1,'2026-01-01')",
        ]:
            connection.execute(text(sql))
        before = {table: connection.execute(text(f'SELECT * FROM {table}')).mappings().all() for table in ('events', 'steps')}
    command.upgrade(config, 'head')
    fields = {'correlation_id', 'causation_id', 'trace_id', 'span_id'}
    assert fields | {'step_id'} <= {c['name'] for c in inspect(engine).get_columns('events')}
    assert fields <= {c['name'] for c in inspect(engine).get_columns('steps')}
    with engine.connect() as connection:
        for table in ('events', 'steps'):
            row = connection.execute(text(f'SELECT * FROM {table}')).mappings().one()
            assert all(row[field] is None for field in fields)
            assert all(row[key] == value for key, value in before[table][0].items())
        assert connection.execute(text('SELECT schema_version FROM events')).scalar_one() == 1
    command.downgrade(config, '0004')
    with engine.connect() as connection:
        for table in ('events', 'steps'):
            assert connection.execute(text(f'SELECT * FROM {table}')).mappings().all() == before[table]
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
    command.upgrade(config, 'head')
    command.downgrade(config, 'base')
    assert inspect(engine).get_table_names() == ['alembic_version']
    engine.dispose()
