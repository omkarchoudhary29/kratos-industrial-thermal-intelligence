import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

cur.execute("SELECT id, task_key, title, priority, status, created_at, created_by_name FROM follow_up_tasks ORDER BY id;")
rows = cur.fetchall()
print(f"Total follow-up tasks: {len(rows)}")
for r in rows:
    print(f"ID: {r[0]}, Key: {r[1]}, Title: {r[2]}, Priority: {r[3]}, Status: {r[4]}, At: {r[5]}, By: {r[6]}")

conn.close()
