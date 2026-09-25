import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

cur.execute("""
    SELECT id, report_key, scope, title, creator_name, status, created_at, 
           evidence_payload->'metadata'->>'scope' as meta_scope,
           approval_trail
    FROM investigation_reports 
    ORDER BY id;
""")
reports = cur.fetchall()
for r in reports:
    print(f"ID {r[0]}: [{r[2]}] {r[3]} | Status: {r[5]} | Created: {r[6]} | By: {r[4]}")

conn.close()
