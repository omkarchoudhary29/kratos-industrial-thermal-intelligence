import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

for table in ["investigation_reports", "authority_submissions", "follow_up_tasks", "follow_up_notes", "data_connectors", "integration_sync_jobs", "system_audit_logs"]:
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position;")
    cols = cur.fetchall()
    print(f"\n--- {table} columns ---")
    for c in cols:
        print(f"  {c[0]} ({c[1]})")

conn.close()
