import sqlite3
import os

db_path = "backend/sql_app.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Users:")
    cursor.execute("SELECT id, email FROM users LIMIT 5")
    print(cursor.fetchall())
    
    print("\nSessions:")
    cursor.execute("SELECT id, title, user_id FROM chat_sessions LIMIT 5")
    print(cursor.fetchall())
    
    print("\nDatasets:")
    cursor.execute("SELECT id, filename, session_id FROM datasets LIMIT 5")
    print(cursor.fetchall())
    
    conn.close()
