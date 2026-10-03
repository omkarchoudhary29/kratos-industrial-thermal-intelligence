import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")

test_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
if not test_url:
    raise RuntimeError("TEST_DATABASE_URL environment variable is required")

conn = psycopg2.connect(test_url)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
for r in cur.fetchall():
    print(r[0])
conn.close()
