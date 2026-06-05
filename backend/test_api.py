import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")

if not api_key:
    print("Error: NVIDIA_API_KEY not found in environment.")
    exit(1)

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False

headers = {
  "Authorization": f"Bearer {api_key}",
  "Accept": "text/event-stream" if stream else "application/json"
}

payload = {
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "messages": [{"role":"user","content":"Hello, are you working?"}],
  "max_tokens": 512,
  "temperature": 1.00,
  "top_p": 1.00,
  "stream": stream
}

print(f"Testing model: {payload['model']}...")
try:
    response = requests.post(invoke_url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
