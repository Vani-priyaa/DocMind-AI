
import sqlite3
import os

db_path = r'e:\CDA\CDA\backend\cda_v3.db'
if not os.path.exists(db_path):
    print(f"File {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        info = cursor.fetchall()
        print(f"Table {table_name}: {info}")
    
    try:
        cursor.execute("SELECT count(*) FROM user;")
        count = cursor.fetchone()[0]
        print(f"User count: {count}")
    
        cursor.execute("SELECT * FROM user;")
        users = cursor.fetchall()
        print(f"Users: {users}")
    except Exception as e:
        print(f"Error checking user table: {e}")
    
    conn.close()
