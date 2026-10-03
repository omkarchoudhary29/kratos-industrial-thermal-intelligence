"""backend/tests/test_credential_isolation.py
-----------------------------------------
Automated validation of test credential removal and database isolation invariants.
Verifies that test environment cannot connect to or mutate operational 'wildfire_db',
and that credentials are strictly loaded via environment rather than tracked code.
"""

import os
from pathlib import Path
import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_hardcoded_database_passwords_in_source():
    """Verify that source files do not contain the exposed plaintext password."""
    # Obfuscated pattern so this test file does not match itself
    forbidden_pattern = "Remote" + "%402006"
    checked_extensions = (".py", ".ts", ".tsx", ".js", ".html")
    ignore_dirs = {".git", "node_modules", ".venv", "backups", "scratch", ".system_generated", "dist"}
    
    violations = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune ignored directories in-place for fast execution
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file == "test_credential_isolation.py":
                continue
            if file.endswith(checked_extensions):
                full_path = Path(root) / file
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    if forbidden_pattern in content:
                        violations.append(str(full_path.relative_to(REPO_ROOT)))
                except Exception:
                    pass

    assert not violations, f"Forbidden hardcoded credential found in: {violations}"


def test_strict_test_database_target():
    """Verify that test database connection resolves strictly to wildfire_test_db."""
    from backend.db.connection import get_db_uri
    from sqlalchemy import create_engine, text

    uri = get_db_uri()
    engine = create_engine(uri)
    with engine.connect() as conn:
        active_db = conn.execute(text("SELECT current_database();")).scalar()
        active_user = conn.execute(text("SELECT current_user;")).scalar()

    assert active_db == "wildfire_test_db", f"Active database must be wildfire_test_db, got {active_db}"
    assert active_db != "wildfire_db", "FATAL: Test connected to operational wildfire_db!"
    assert active_user == "wildfire_test_user", f"Test should connect as isolated wildfire_test_user, got {active_user}"


def test_test_user_is_strictly_denied_operational_db():
    """Verify that wildfire_test_user is blocked by PostgreSQL from connecting to wildfire_db."""
    test_db_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    assert test_db_url, "TEST_DATABASE_URL must be defined"

    # Attempt connection to operational wildfire_db using test user credentials
    operational_url_with_test_user = test_db_url.rsplit("/", 1)[0] + "/wildfire_db"
    with pytest.raises(psycopg2.OperationalError) as exc_info:
        psycopg2.connect(operational_url_with_test_user)
    
    assert "permission denied" in str(exc_info.value).lower() or "fatal" in str(exc_info.value).lower()
