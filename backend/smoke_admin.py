import requests

s = requests.Session()
r = s.post("http://127.0.0.1:8000/api/admin/auth/login", json={"username": "admin", "password": "admin123"})
print("login", r.status_code, r.json().get("username"), "admin=", r.json().get("is_admin"))
print("stats", s.get("http://127.0.0.1:8000/api/admin/stats").json())
reports = s.get("http://127.0.0.1:8000/api/admin/reports", params={"status": "all"}).json()
print("reports", len(reports))
for x in reports[:3]:
    print(" ", x["id"], x["type"], x["status"], x["content"][:16])
print("users", len(s.get("http://127.0.0.1:8000/api/admin/users").json()))
print("circles", len(s.get("http://127.0.0.1:8000/api/admin/circles").json()))
print("audit", len(s.get("http://127.0.0.1:8000/api/admin/audit").json()))
# dismiss first pending
pend = [x for x in reports if x["status"] == "pending"]
if pend:
    r = s.post(
        f"http://127.0.0.1:8000/api/admin/reports/{pend[0]['id']}/dismiss",
        json={"reason": "未发现违规", "note": "smoke"},
    )
    print("dismiss", r.status_code, r.json())
