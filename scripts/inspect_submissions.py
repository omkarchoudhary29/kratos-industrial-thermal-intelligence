import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

cur.execute("SELECT id, submission_key, report_id, authority_name, channel, reference_number, submitted_by, submitted_at, status, notes, receipt_metadata FROM authority_submissions ORDER BY id;")
rows = cur.fetchall()
print(f"Total submissions: {len(rows)}")
for r in rows:
    print(f"ID: {r[0]}, Key: {r[1]}, ReportID: {r[2]}, Auth: {r[3]}, Channel: {r[4]}, Ref: {r[5]}, By: {r[6]}, At: {r[7]}, Status: {r[8]}, Notes: {r[9]}, Meta: {r[10]}")

conn.close()
