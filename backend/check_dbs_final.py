
import sqlite3
import os

db_path1 = r'e:\CDA\CDA\backend\cda_v3.db'
db_path2 = r'e:\CDA\CDA\sql_app.db'

def check_db(db_path):
    print(f"Checking {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"Tables: {tables}")
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"Table {table}: {count} rows")
        if table in ['users', 'user']:
            c.execute(f"SELECT * FROM {table} LIMIT 5")
            rows = c.fetchall()
            for row in rows:
                print(f"  Row: {row}")
    conn.close()

check_db(db_path1)
print("-" * 20)
check_db(db_path2)
