-- deploy/sql/01_setup_least_privilege_role.sql
-- =============================================================================
-- Least-Privilege Application Runtime Role for KRATOS V3.1
-- =============================================================================
-- Separates DDL/Administrative migration authority from the runtime application role.
--
-- Security Properties:
-- 1. NOSUPERUSER: Cannot execute administrative cluster operations.
-- 2. NOCREATEDB: Cannot create or drop databases.
-- 3. NOCREATEROLE: Cannot create, modify, or elevate PostgreSQL user accounts.
-- 4. NON-OWNER: Does NOT own tables or triggers; cannot disable or bypass
--    the append-only cryptographic audit trigger on system_audit_logs.
-- 5. RUNTIME CRUD: Granted strict DML access (SELECT, INSERT, UPDATE, DELETE)
--    on application domain tables, and USAGE/SELECT/UPDATE on sequences.
-- =============================================================================

-- Step 1: Create Role with placeholder password (change before applying in production)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'kratos_app_user') THEN
        CREATE ROLE kratos_app_user WITH 
            LOGIN 
            NOSUPERUSER 
            NOCREATEDB 
            NOCREATEROLE 
            NOINHERIT 
            PASSWORD 'REPLACE_WITH_SECURE_GENERATED_PASSWORD';
        RAISE NOTICE 'Role kratos_app_user created.';
    ELSE
        ALTER ROLE kratos_app_user WITH 
            NOSUPERUSER 
            NOCREATEDB 
            NOCREATEROLE;
        RAISE NOTICE 'Role kratos_app_user already exists. Permissions constrained.';
    END IF;
END $$;

-- Step 2: Database Connection
REVOKE ALL ON DATABASE wildfire_db FROM PUBLIC;
GRANT CONNECT ON DATABASE wildfire_db TO kratos_app_user;

-- Step 3: Schema Permissions
GRANT USAGE ON SCHEMA public TO kratos_app_user;

-- Step 4: Table DML Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kratos_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kratos_app_user;

-- Step 5: Sequence Grants (Required for primary key autoincrements)
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO kratos_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO kratos_app_user;

-- Step 6: PostGIS Read Permissions
GRANT SELECT ON spatial_ref_sys TO kratos_app_user;

-- Step 7: Explicitly prohibit DDL modifications
-- Note: As a non-owner of system_audit_logs, kratos_app_user cannot ALTER TABLE,
-- DROP TRIGGER, or DISABLE TRIGGER.
REVOKE CREATE ON SCHEMA public FROM kratos_app_user;

-- =============================================================================
-- ROLLBACK SCRIPT (Execute as superuser to decommission role):
-- REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM kratos_app_user;
-- REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM kratos_app_user;
-- REVOKE USAGE ON SCHEMA public FROM kratos_app_user;
-- REVOKE CONNECT ON DATABASE wildfire_db FROM kratos_app_user;
-- DROP ROLE IF EXISTS kratos_app_user;
-- =============================================================================
