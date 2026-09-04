#!/usr/bin/env python3
"""scripts/setup_test_credentials.py
-----------------------------------
Rotates the dedicated test database credential for wildfire_test_db.
Creates/updates role 'wildfire_test_user' with a fresh secure password.
Grants full privileges on wildfire_test_db and explicitly revokes access to wildfire_db.
Saves the connection string to gitignored .env.test.
"""

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

admin_db_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
if not admin_db_url:
    print("Error: DATABASE_URL not set in .env")
    sys.exit(1)


def rotate_test_credentials():
    new_password = secrets.token_urlsafe(24)
    escaped_password = new_password.replace("'", "''")
    
    print("Connecting as admin to PostgreSQL...")
    conn = psycopg2.connect(admin_db_url)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Create or update role
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'wildfire_test_user';")
    exists = cur.fetchone()
    if exists:
        print("Role 'wildfire_test_user' exists. Rotating password...")
        cur.execute(f"ALTER ROLE wildfire_test_user WITH LOGIN PASSWORD '{escaped_password}';")
    else:
        print("Creating role 'wildfire_test_user'...")
        cur.execute(f"CREATE ROLE wildfire_test_user WITH LOGIN PASSWORD '{escaped_password}';")

    # 2. Restrict operational database
    print("Revoking permissions on operational database 'wildfire_db'...")
    cur.execute("REVOKE ALL ON DATABASE wildfire_db FROM wildfire_test_user;")
    cur.execute("REVOKE CONNECT ON DATABASE wildfire_db FROM wildfire_test_user;")
    cur.execute("REVOKE CONNECT ON DATABASE wildfire_db FROM PUBLIC;")
    cur.execute("GRANT CONNECT ON DATABASE wildfire_db TO postgres;")

    # 3. Grant test database permissions
    print("Granting permissions on 'wildfire_test_db'...")
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE wildfire_test_db TO wildfire_test_user;")
    cur.execute("GRANT CONNECT ON DATABASE wildfire_test_db TO wildfire_test_user;")
    conn.close()

    # 4. Connect to wildfire_test_db to grant table and schema privileges
    test_admin_url = admin_db_url.rsplit("/", 1)[0] + "/wildfire_test_db"
    conn_test = psycopg2.connect(test_admin_url)
    conn_test.autocommit = True
    cur_test = conn_test.cursor()

    cur_test.execute("GRANT USAGE, CREATE ON SCHEMA public TO wildfire_test_user;")
    cur_test.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wildfire_test_user;")
    cur_test.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wildfire_test_user;")
    cur_test.execute("GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO wildfire_test_user;")
    cur_test.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO wildfire_test_user;")
    cur_test.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO wildfire_test_user;")

    # Transfer ownership of all public tables and sequences in wildfire_test_db to wildfire_test_user
    cur_test.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    for t in cur_test.fetchall():
        cur_test.execute(f'ALTER TABLE "{t[0]}" OWNER TO wildfire_test_user;')

    cur_test.execute("""
        SELECT sequence_name FROM information_schema.sequences 
        WHERE sequence_schema = 'public';
    """)
    for s in cur_test.fetchall():
        cur_test.execute(f'ALTER SEQUENCE "{s[0]}" OWNER TO wildfire_test_user;')
    print("✓ Ownership of all tables and sequences in wildfire_test_db transferred to wildfire_test_user")
    conn_test.close()

    # 5. Write to .env.test (gitignored via .env.* in .gitignore)
    test_db_url = f"postgresql+psycopg2://wildfire_test_user:{quote_plus(new_password)}@localhost:5432/wildfire_test_db"
    env_test_path = REPO_ROOT / ".env.test"
    with open(env_test_path, "w", encoding="utf-8") as f:
        f.write("# Auto-generated rotated test credentials (gitignored)\n")
        f.write(f"TEST_DATABASE_URL={test_db_url}\n")
        f.write("TEST_DB_NAME=wildfire_test_db\n")
        f.write("TESTING=1\n")

    print(f"✓ Rotated test credentials saved to {env_test_path.name}")

    # 6. Verify connection to wildfire_test_db
    try:
        conn_verify = psycopg2.connect(f"postgresql://wildfire_test_user:{new_password}@localhost:5432/wildfire_test_db")
        cur_v = conn_verify.cursor()
        cur_v.execute("SELECT current_database(), current_user;")
        db_res, user_res = cur_v.fetchone()
        print(f"✓ Test connection verified: database={db_res}, user={user_res}")
        conn_verify.close()
    except Exception as e:
        print(f"✗ Failed to connect to test db: {e}")
        sys.exit(1)

    # 7. Verify CANNOT connect to wildfire_db
    try:
        psycopg2.connect(f"postgresql://wildfire_test_user:{new_password}@localhost:5432/wildfire_db")
        print("✗ ERROR: wildfire_test_user was unexpectedly able to connect to wildfire_db!")
        sys.exit(1)
    except psycopg2.OperationalError:
        print("✓ Security verified: wildfire_test_user is strictly DENIED connection to wildfire_db.")


if __name__ == "__main__":
    rotate_test_credentials()
