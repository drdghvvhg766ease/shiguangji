import requests

print("backend health", requests.get("http://127.0.0.1:8000/api/health", timeout=5).text)
print("5173 health", requests.get("http://127.0.0.1:5173/api/health", timeout=5).text)
print("5174 health", requests.get("http://127.0.0.1:5174/api/health", timeout=5).text)

s = requests.Session()
r = s.post(
    "http://127.0.0.1:5173/api/auth/login",
    json={"username": "demo_a", "password": "demo1234"},
    timeout=10,
)
print("login via 5173", r.status_code, r.json())
r = s.get("http://127.0.0.1:5173/api/circles", timeout=10)
print("circles via 5173", r.status_code, r.json())

s2 = requests.Session()
r = s2.post(
    "http://127.0.0.1:5174/api/admin/auth/login",
    json={"username": "admin", "password": "admin123"},
    timeout=10,
)
print("admin login via 5174", r.status_code, r.json().get("username"), r.json().get("is_admin"))
r = s2.get("http://127.0.0.1:5174/api/admin/stats", timeout=10)
print("admin stats via 5174", r.status_code, r.json())
