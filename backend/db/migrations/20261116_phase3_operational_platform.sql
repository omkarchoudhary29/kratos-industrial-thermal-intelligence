-- Migration: 20261116_phase3_operational_platform.sql
-- Description: Phase 3 Operational Platform Schema Extensions
-- Tables: authority_submissions, data_connectors, integration_sync_jobs, system_audit_logs
-- Schema enhancements: investigation_reports (version, pdf_path, csv_path, submission_status, approval_trail)
--                      follow_up_tasks (evidence_attachments, audit_trail)

-- 1. Enhance investigation_reports
ALTER TABLE investigation_reports 
    ADD COLUMN IF NOT EXISTS version VARCHAR(16) DEFAULT 'v1.0',
    ADD COLUMN IF NOT EXISTS pdf_path VARCHAR(255),
    ADD COLUMN IF NOT EXISTS csv_path VARCHAR(255),
    ADD COLUMN IF NOT EXISTS submission_status VARCHAR(32) DEFAULT 'NOT_SUBMITTED',
    ADD COLUMN IF NOT EXISTS approval_trail JSONB;

-- 2. Enhance follow_up_tasks
ALTER TABLE follow_up_tasks 
    ADD COLUMN IF NOT EXISTS evidence_attachments JSONB,
    ADD COLUMN IF NOT EXISTS audit_trail JSONB;

-- 3. Authority Submissions Table
CREATE TABLE IF NOT EXISTS authority_submissions (
    id SERIAL PRIMARY KEY,
    submission_key VARCHAR(64) UNIQUE NOT NULL,
    report_id INTEGER REFERENCES investigation_reports(id) ON DELETE SET NULL,
    report_key VARCHAR(64) NOT NULL,
    authority_id VARCHAR(64) NOT NULL,
    authority_name VARCHAR(255) NOT NULL,
    purpose VARCHAR(128) NOT NULL,
    channel VARCHAR(64) NOT NULL,
    reference_number VARCHAR(128) NOT NULL,
    acknowledgement_number VARCHAR(128),
    submitted_by VARCHAR(128) NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED',
    notes TEXT,
    receipt_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_authority_submissions_report_id ON authority_submissions(report_id);
CREATE INDEX IF NOT EXISTS ix_authority_submissions_authority_id ON authority_submissions(authority_id);
CREATE INDEX IF NOT EXISTS ix_authority_submissions_status ON authority_submissions(status);
CREATE INDEX IF NOT EXISTS ix_authority_submissions_created_at ON authority_submissions(created_at DESC);

-- 4. Data Connectors Table
CREATE TABLE IF NOT EXISTS data_connectors (
    id SERIAL PRIMARY KEY,
    connector_key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    connector_type VARCHAR(64) NOT NULL,
    endpoint_url TEXT NOT NULL,
    auth_type VARCHAR(32) NOT NULL DEFAULT 'NONE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    health_status VARCHAR(32) NOT NULL DEFAULT 'HEALTHY',
    last_checked_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    records_received INTEGER DEFAULT 0,
    records_accepted INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    configuration JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_data_connectors_key ON data_connectors(connector_key);
CREATE INDEX IF NOT EXISTS ix_data_connectors_health ON data_connectors(health_status);

-- 5. Integration Sync Jobs Table
CREATE TABLE IF NOT EXISTS integration_sync_jobs (
    id SERIAL PRIMARY KEY,
    job_key VARCHAR(64) UNIQUE NOT NULL,
    connector_id INTEGER REFERENCES data_connectors(id) ON DELETE CASCADE,
    connector_key VARCHAR(64) NOT NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_seconds FLOAT,
    status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
    records_fetched INTEGER DEFAULT 0,
    records_accepted INTEGER DEFAULT 0,
    duplicates_dropped INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    error_message TEXT,
    checkpoint_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_integration_sync_jobs_connector_id ON integration_sync_jobs(connector_id);
CREATE INDEX IF NOT EXISTS ix_integration_sync_jobs_status ON integration_sync_jobs(status);
CREATE INDEX IF NOT EXISTS ix_integration_sync_jobs_created_at ON integration_sync_jobs(created_at DESC);

-- 6. System Audit Logs Table
CREATE TABLE IF NOT EXISTS system_audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(128) NOT NULL,
    user_role VARCHAR(64) NOT NULL DEFAULT 'Monitoring Analyst',
    action_type VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128),
    ip_address VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    details JSONB
);

CREATE INDEX IF NOT EXISTS ix_system_audit_logs_timestamp ON system_audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_system_audit_logs_action ON system_audit_logs(action_type);
CREATE INDEX IF NOT EXISTS ix_system_audit_logs_user_id ON system_audit_logs(user_id);
