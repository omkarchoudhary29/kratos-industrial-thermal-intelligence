import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")


def sync():
    src_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
    dst_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    if not src_url or not dst_url:
        raise RuntimeError("DATABASE_URL and TEST_DATABASE_URL must be configured")

    conn_src = psycopg2.connect(src_url)
    conn_dst = psycopg2.connect(dst_url)
    
    # Truncate in reverse foreign key order
    tables = ['authority_submissions', 'follow_up_notes', 'follow_up_tasks', 'investigation_reports', 'system_audit_logs']
    cur_dst = conn_dst.cursor()
    for t in tables:
        cur_dst.execute(f'TRUNCATE TABLE {t} CASCADE;')
    conn_dst.commit()

    # Insert in forward foreign key order
    forward_tables = ['investigation_reports', 'follow_up_tasks', 'follow_up_notes', 'authority_submissions', 'system_audit_logs']
    for t in forward_tables:
        cur_src = conn_src.cursor()
        cur_src.execute(f'SELECT * FROM {t}')
        rows = cur_src.fetchall()
        colnames = [desc[0] for desc in cur_src.description]
        if rows:
            col_list = ', '.join([f'"{c}"' for c in colnames])
            placeholders = ', '.join(['%s'] * len(colnames))
            insert_sql = f'INSERT INTO {t} ({col_list}) VALUES ({placeholders})'
            cur_dst.executemany(insert_sql, rows)
            conn_dst.commit()
        print(f'Successfully copied {len(rows)} rows to wildfire_test_db.{t}')
        
    conn_src.close()
    conn_dst.close()


if __name__ == '__main__':
    sync()
