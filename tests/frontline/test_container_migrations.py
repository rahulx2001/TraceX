"""Exercise deployment ordering, including real ledger writes after migrations."""
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from scripts.migrate import _ensure_log_duckdb, migrate_duckdb
from src.data.schema import OPS_SCHEMA_SQL
from src.data.warehouse import apply_ops_schema
from src.ledger.writer import AgentAction, _insert_action_row

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('legacy', [False, True])
def test_migrations_allow_current_ledger_and_case_writes(tmp_path, legacy):
    path = tmp_path / 'ops.duckdb'
    if legacy:
        with duckdb.connect(str(path)) as con:
            con.execute((ROOT / 'migrations/001_ops_init.sql').read_text())
            con.execute("INSERT INTO agent_actions (action_id, interaction_id, agent, action_type, created_at, row_hash) VALUES ('old', 'prior', 'intake', 'observation', TIMESTAMPTZ '2026-10-29 10:00:00+05:30', 'keep-original-hash')")
            con.execute("INSERT INTO cases (case_id, description_summary) VALUES ('prior-case', 'Keep this report')")
    assert '004' in migrate_duckdb(path)
    assert migrate_duckdb(path) == []
    with duckdb.connect(str(path)) as con, duckdb.connect(':memory:') as canonical:
        apply_ops_schema(con)
        canonical.execute(OPS_SCHEMA_SQL)
        for table in ('interactions', 'cases', 'agent_actions'):
            expected = {row[1] for row in canonical.execute(f"PRAGMA table_info('{table}')").fetchall()}
            actual = {row[1] for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()}
            assert expected <= actual
        action = AgentAction(interaction_id='new-report', agent='orchestrator', action_type='interaction_started')
        assert _insert_action_row(con, action)
        con.execute("INSERT INTO cases (case_id, interaction_id, pack_id, created_at, severity, severity_source, priority, safety_flags, investigation_id) VALUES ('new-case', 'new-report', 'automotive_nhtsa', CURRENT_TIMESTAMP, 'Low', 'rules', 4, '{}', NULL)")
        if legacy:
            assert con.execute("SELECT ts, row_hash FROM agent_actions WHERE action_id='old'").fetchone() == (datetime(2026, 10, 29, 4, 30), 'keep-original-hash')
            assert con.execute("SELECT description_summary, severity_source FROM cases WHERE case_id='prior-case'").fetchone() == ('Keep this report', None)


def test_migration_keeps_existing_current_ledger_timestamp_and_hash(tmp_path):
    path = tmp_path / 'current.duckdb'
    with duckdb.connect(str(path)) as con:
        apply_ops_schema(con)
        # init_ops_db on the previous release stamped its then-current 001.
        _ensure_log_duckdb(con)
        con.execute("INSERT INTO schema_migrations (version, name) VALUES ('001', '001_ops_init.sql')")
        action = AgentAction(interaction_id='current-report', agent='orchestrator', action_type='interaction_started')
        _insert_action_row(con, action)
        before = con.execute('SELECT ts, row_hash, prev_hash FROM agent_actions').fetchall()
    migrate_duckdb(path)
    with duckdb.connect(str(path)) as con:
        assert con.execute('SELECT ts, row_hash, prev_hash FROM agent_actions').fetchall() == before
