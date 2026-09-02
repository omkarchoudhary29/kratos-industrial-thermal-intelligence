-- Migration: 20261117_cryptographic_audit_hash_chain.sql
-- Description: Adds previous_record_hash, integrity_version, and hash_backfilled_at to system_audit_logs.
--              Installs PostgreSQL BEFORE UPDATE OR DELETE rejection trigger for append-only immutability.

-- 1. Schema Extensions
ALTER TABLE system_audit_logs 
    ADD COLUMN IF NOT EXISTS previous_record_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS integrity_version VARCHAR(16) DEFAULT 'v2_chain',
    ADD COLUMN IF NOT EXISTS hash_backfilled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_system_audit_logs_previous_hash ON system_audit_logs(previous_record_hash);
CREATE INDEX IF NOT EXISTS ix_system_audit_logs_integrity_hash ON system_audit_logs(integrity_hash);

-- 2. Database Immutability Trigger
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'system_audit_logs is an append-only cryptographic ledger. UPDATE and DELETE operations are strictly prohibited.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_audit_log_modification ON system_audit_logs;
CREATE TRIGGER trg_prevent_audit_log_modification
BEFORE UPDATE OR DELETE ON system_audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
