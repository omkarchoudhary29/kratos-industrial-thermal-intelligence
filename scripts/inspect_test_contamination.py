import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

print("=== Investigation Reports ===")
cur.execute("SELECT id, title, scope, created_at, status FROM investigation_reports ORDER BY id;")
reports = cur.fetchall()
for r in reports:
    print(r)
print(f"Total reports: {len(reports)}")

print("\n=== Authority Submissions ===")
cur.execute("SELECT id, report_id, authority_name, submission_channel, reference_number, submitted_at, status FROM authority_submissions ORDER BY id;")
subs = cur.fetchall()
for s in subs:
    print(s)
print(f"Total submissions: {len(subs)}")

print("\n=== Follow Up Tasks ===")
cur.execute("SELECT id, title, priority, status, created_at FROM follow_up_tasks ORDER BY id;")
tasks = cur.fetchall()
for t in tasks:
    print(t)
print(f"Total tasks: {len(tasks)}")

print("\n=== System Audit Logs ===")
cur.execute("SELECT id, action, target_type, target_id, timestamp, operator_id FROM system_audit_logs ORDER BY id;")
logs = cur.fetchall()
for l in logs:
    print(l)
print(f"Total audit logs: {len(logs)}")

conn.close()
