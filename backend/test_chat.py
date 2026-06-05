import requests
import json
import sys

base_url = "http://127.0.0.1:8000/api/v1"
headers = {"Content-Type": "application/json"}

# 1. Create Session (Skipped, using existing session 2)
session_id = 2

# 2. Upload File (Skipping upload for existing session)

# 3. Chat
print(f"Sending message to session {session_id}...")
payload = {"query": "describe the data"}
try:
    resp = requests.post(f"{base_url}/chat/{session_id}/send", json=payload, headers=headers)
    print(f"Chat Status: {resp.status_code}")
    print(f"Chat Response: {resp.text}")
except Exception as e:
    print(f"Chat request failed: {e}")
