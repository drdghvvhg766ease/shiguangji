import requests

s = requests.Session()
s.post("http://127.0.0.1:8000/api/auth/login", json={"username": "demo_a", "password": "demo1234"})
for c in s.get("http://127.0.0.1:8000/api/circles").json():
    print("circle", c["id"], c["name"], "members", c["member_count"])
    posts = s.get(f"http://127.0.0.1:8000/api/circles/{c['id']}/posts").json()
    print("  posts", len(posts))
    for p in posts:
        print("   ", p["id"], p["event_date"], (p["content"] or "")[:20], "media", len(p["media"]))
