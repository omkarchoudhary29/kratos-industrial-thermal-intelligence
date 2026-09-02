import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public' 
      AND table_name NOT IN ('geometry_columns', 'geography_columns', 'spatial_ref_sys') 
    ORDER BY table_name;
""")

print("=== PostgreSQL Table Row Counts ===")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    cur.execute(f'SELECT count(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    print(f"{t}: {cnt}")

conn.close()
