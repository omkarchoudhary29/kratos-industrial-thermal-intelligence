-- Migration: 20261116_final_hardening_audit_and_test_isolation.sql
-- Description: Adds is_test flag to operational tables, marks existing test-generated records,
--              and adds tamper-evident integrity hash to system_audit_logs.

-- 1. Add is_test column to investigation_reports
ALTER TABLE investigation_reports 
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX IF NOT EXISTS ix_investigation_reports_is_test ON investigation_reports(is_test);

-- 2. Add is_test column to follow_up_tasks
ALTER TABLE follow_up_tasks 
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_is_test ON follow_up_tasks(is_test);

-- 3. Add is_test column to authority_submissions
ALTER TABLE authority_submissions 
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX IF NOT EXISTS ix_authority_submissions_is_test ON authority_submissions(is_test);

-- 4. Add is_test and integrity_hash columns to system_audit_logs
ALTER TABLE system_audit_logs 
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS integrity_hash VARCHAR(64);
CREATE INDEX IF NOT EXISTS ix_system_audit_logs_is_test ON system_audit_logs(is_test);

-- 5. Mark known test-generated records in authority_submissions
UPDATE authority_submissions 
SET is_test = TRUE,
    notes = COALESCE(notes, '') || ' [TEST_PROVENANCE: Automated test suite dispatch]'
WHERE reference_number LIKE '%TEST%' 
   OR notes ILIKE '%regression%'
   OR notes ILIKE '%automated%';

-- 6. Mark known test-generated records in follow_up_tasks
UPDATE follow_up_tasks
SET is_test = TRUE,
    description = COALESCE(description, '') || ' [TEST_PROVENANCE: Automated test task]'
WHERE feature_id LIKE '%test_%'
   OR title ILIKE '%Metallurgical Complex%'
   OR title ILIKE '%Secondary Bastar Task%'
   OR title ILIKE '%Primary Bastar Flare Inspection%';

-- 7. Mark known test-generated records in investigation_reports
UPDATE investigation_reports
SET is_test = TRUE,
    summary_text = COALESCE(summary_text, '') || ' [TEST_PROVENANCE: Automated test report]'
WHERE title ILIKE '%Comprehensive Bastar Corridor Environmental Audit%'
   OR title ILIKE '%Eastern Industrial Corridor Viewport Dossier%'
   OR title ILIKE '%Korba Approval Workflow Audit%';

-- 8. Mark known test audit logs
UPDATE system_audit_logs
SET is_test = TRUE
WHERE details::text ILIKE '%TEST%' 
   OR resource_id ILIKE '%test%';
