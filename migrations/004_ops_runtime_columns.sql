-- Complete the legacy 001 skeleton for current DuckDB runtime writes.
-- target: ops
-- Additive: retain original records, columns, timestamps and ledger hashes.
-- Unknown historical case fields remain NULL rather than inferred facts.

ALTER TABLE cases ADD COLUMN IF NOT EXISTS onset TIMESTAMP;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS severity_source VARCHAR;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS priority INTEGER;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS safety_flags JSON;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS advisory_match_id VARCHAR;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS cluster_match_id INTEGER;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS investigation_id VARCHAR;

ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS case_id VARCHAR;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS evidence_ids JSON;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS ok BOOLEAN DEFAULT TRUE;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS error VARCHAR;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS duration_ms INTEGER;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS ts TIMESTAMP;
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS schema_version INTEGER DEFAULT 1;
-- Current-schema databases have ts already but may not have created_at.
ALTER TABLE agent_actions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
UPDATE agent_actions SET ts = timezone('UTC', created_at)
    WHERE ts IS NULL AND created_at IS NOT NULL;
