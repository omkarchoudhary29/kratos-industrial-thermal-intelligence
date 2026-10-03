"""conftest.py
Root pytest configuration for KRATOS V3.1 test isolation.
Redirects all automated database operations to dedicated isolated test database 'wildfire_test_db'.
Operational database 'wildfire_db' remains 100% pristine and unmutated during test runs.
Strictly requires TEST_DATABASE_URL environment variable; never falls back to DATABASE_URL.
"""

import os
import sys
from pathlib import Path
import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
# Load dedicated test environment if present, then base env
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")

# Ensure backend root is in sys.path
backend_dir = REPO_ROOT / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Enforce isolated test database target from environment
test_db_uri = os.getenv("TEST_DATABASE_URL")
if not test_db_uri:
    # Build from components if provided
    test_user = os.getenv("TEST_DB_USER", "wildfire_test_user")
    test_pass = os.getenv("TEST_DB_PASSWORD")
    test_host = os.getenv("TEST_DB_HOST", "localhost")
    test_port = os.getenv("TEST_DB_PORT", "5432")
    test_name = os.getenv("TEST_DB_NAME", "wildfire_test_db")
    if test_pass:
        from urllib.parse import quote_plus
        test_db_uri = f"postgresql+psycopg2://{test_user}:{quote_plus(test_pass)}@{test_host}:{test_port}/{test_name}"

if not test_db_uri:
    raise RuntimeError(
        "CRITICAL TEST ISOLATION ERROR: Neither TEST_DATABASE_URL nor TEST_DB_PASSWORD is set. "
        "Automated tests are strictly prohibited from falling back to operational DATABASE_URL."
    )

# Strictly reject any test URI that targets operational database
if "wildfire_db" in test_db_uri and "wildfire_test_db" not in test_db_uri:
    raise RuntimeError("FATAL SECURITY BREACH: TEST_DATABASE_URL must never target operational 'wildfire_db'!")

os.environ["DATABASE_URL"] = test_db_uri
os.environ["DB_NAME"] = "wildfire_test_db"
os.environ["TESTING"] = "1"
os.environ["ALLOW_SQLITE_FALLBACK"] = "0"


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_isolation():
    """Verify live database connection connects strictly to wildfire_test_db via SQL query."""
    try:
        from db.connection import get_db_uri
    except ImportError:
        from backend.db.connection import get_db_uri
    
    uri = get_db_uri()
    assert "wildfire_test_db" in uri, "CRITICAL: Tests must NOT run against operational DB!"
    assert "wildfire_db" not in uri.split("/")[-1].split("?")[0] or uri.split("/")[-1].startswith("wildfire_test_db"), \
        "CRITICAL: Active database URI resolves to operational DB!"

    # Perform live database identity assertion using SQLAlchemy
    from sqlalchemy import create_engine, text
    engine = create_engine(uri)
    with engine.connect() as conn:
        active_db = conn.execute(text("SELECT current_database();")).scalar()
        active_user = conn.execute(text("SELECT current_user;")).scalar()
        assert active_db == "wildfire_test_db", f"CRITICAL: Live connection resolved to '{active_db}', expected 'wildfire_test_db'!"
        assert active_db != "wildfire_db", "FATAL: Live connection resolved to operational database 'wildfire_db'!"

    yield
