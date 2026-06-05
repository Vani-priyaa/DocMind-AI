
import sqlite3
import os

db_path = r'e:\CDA\CDA\backend\cda_v3.db'
if not os.path.exists(db_path):
    print(f"File {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    users = cursor.fetchall()
    print(f"Users: {users}")
    conn.close()
