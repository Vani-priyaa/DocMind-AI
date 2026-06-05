
import sqlite3
import os

db_paths = [
    r'e:\CDA\CDA\backend\cda_v3.db',
    r'e:\CDA\CDA\sql_app.db'
]

for db_path in db_paths:
    print(f"--- Checking {db_path} ---")
    if not os.path.exists(db_path):
        print(f"File {db_path} not found")
        continue
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        if ('users',) in tables:
            cursor.execute("SELECT * FROM users;")
            users = cursor.fetchall()
            print(f"Users: {users}")
        elif ('user',) in tables:
            cursor.execute("SELECT * FROM user;")
            users = cursor.fetchall()
            print(f"Users: {users}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
