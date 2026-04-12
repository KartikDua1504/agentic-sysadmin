from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)
response = client.post("/reset", json={})
print(response.status_code)
print(response.json())
