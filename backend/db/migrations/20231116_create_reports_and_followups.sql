-- Migration: 20231116_create_reports_and_followups.sql
-- Description: Creates persistent storage for Investigation Reports and Follow-Up Tasks

CREATE TABLE IF NOT EXISTS investigation_reports (
    id SERIAL PRIMARY KEY,
    report_key VARCHAR(64) UNIQUE NOT NULL,
    scope VARCHAR(32) NOT NULL, -- 'region', 'viewport', 'feature'
    region_id VARCHAR(64),
    region_name VARCHAR(128),
    feature_type VARCHAR(32), -- 'cluster', 'observation', 'facility'
    feature_id VARCHAR(64),
    title VARCHAR(255) NOT NULL,
    bounds JSONB,
    time_range_start TIMESTAMPTZ,
    time_range_end TIMESTAMPTZ,
    evidence_payload JSONB NOT NULL,
    summary_text TEXT,
    sections JSONB,
    creator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    creator_name VARCHAR(128),
    status VARCHAR(32) DEFAULT 'generated',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_investigation_reports_scope ON investigation_reports(scope);
CREATE INDEX IF NOT EXISTS ix_investigation_reports_region_id ON investigation_reports(region_id);
CREATE INDEX IF NOT EXISTS ix_investigation_reports_feature ON investigation_reports(feature_type, feature_id);
CREATE INDEX IF NOT EXISTS ix_investigation_reports_created_at ON investigation_reports(created_at DESC);

CREATE TABLE IF NOT EXISTS follow_up_tasks (
    id SERIAL PRIMARY KEY,
    task_key VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    feature_type VARCHAR(32) NOT NULL, -- 'cluster', 'observation', 'facility', 'region'
    feature_id VARCHAR(64) NOT NULL,
    region_name VARCHAR(128),
    report_id INTEGER REFERENCES investigation_reports(id) ON DELETE SET NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM', -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'IN_PROGRESS', 'AWAITING_VERIFICATION', 'RESOLVED', 'CLOSED'
    description TEXT,
    assigned_to VARCHAR(128),
    due_date TIMESTAMPTZ,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_by_name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_status ON follow_up_tasks(status);
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_priority ON follow_up_tasks(priority);
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_feature ON follow_up_tasks(feature_type, feature_id);
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_created_at ON follow_up_tasks(created_at DESC);

CREATE TABLE IF NOT EXISTS follow_up_notes (
    id SERIAL PRIMARY KEY,
    follow_up_id INTEGER NOT NULL REFERENCES follow_up_tasks(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    author_name VARCHAR(128) NOT NULL,
    note_text TEXT NOT NULL,
    status_change VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_follow_up_notes_follow_up_id ON follow_up_notes(follow_up_id);
