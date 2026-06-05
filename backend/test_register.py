
import requests

url = "http://127.0.0.1:8000/api/v1/auth/register"
data = {
    "email": "test_new@example.com",
    "password": "password123"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
