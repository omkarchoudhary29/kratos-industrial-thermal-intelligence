import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL").replace("+psycopg2", ""))
cur = conn.cursor()

cur.execute("SELECT id, connector_key, name, provider, connector_type, endpoint_url, health_status, last_checked_at, last_sync_at, records_received FROM data_connectors ORDER BY id;")
rows = cur.fetchall()
print(f"Total data connectors: {len(rows)}")
for r in rows:
    print(f"ID {r[0]}: {r[1]} | {r[2]} ({r[3]}) | Type: {r[4]} | Health: {r[6]} | Records: {r[9]} | URL: {r[5]}")

conn.close()
