"""pytest 覆盖：认证、圈子权限、媒体哈希、Range、猜照片池。

前置：后端已在 127.0.0.1:8000 运行；数据库可写。
运行：python -m pytest app_tests.py -q
或：  python app_tests.py
"""
from __future__ import annotations

import hashlib
import io
import os
import sys

import pytest
import requests
from PIL import Image

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")


def _photo(color=(224, 122, 95), size=(800, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture()
def s():
    return requests.Session()


def test_health(s):
    r = s.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_register_login_me(s):
    name = "pytest_user_1"
    s.post(f"{BASE}/api/auth/register", json={"username": name, "password": "pass1234", "nickname": "测"}, timeout=10)
    r = s.post(f"{BASE}/api/auth/login", json={"username": name, "password": "pass1234"}, timeout=10)
    assert r.status_code == 200
    r = s.get(f"{BASE}/api/auth/me", timeout=10)
    assert r.json()["username"] == name


def test_circle_invite_and_member_gate(s):
    # owner
    r = s.post(f"{BASE}/api/auth/login", json={"username": "demo_a", "password": "demo1234"}, timeout=10)
    assert r.status_code == 200
    r = s.post(f"{BASE}/api/circles", json={"name": "PY圈子"}, timeout=10)
    cid, code = r.json()["id"], r.json()["invite_code"]

    # outsider
    s2 = requests.Session()
    s2.post(f"{BASE}/api/auth/login", json={"username": "demo_b", "password": "demo1234"}, timeout=10)
    # wait, demo_b is already in 我们仨 but not in this new circle
    r = s2.get(f"{BASE}/api/circles/{cid}/posts", timeout=10)
    assert r.status_code == 403

    r = s2.post(f"{BASE}/api/circles/join", json={"invite_code": code}, timeout=10)
    assert r.status_code == 200
    r = s2.get(f"{BASE}/api/circles/{cid}/posts", timeout=10)
    assert r.status_code == 200


def test_upload_export_sha256_and_range_headers(s):
    s.post(f"{BASE}/api/auth/login", json={"username": "demo_a", "password": "demo1234"}, timeout=10)
    circles = s.get(f"{BASE}/api/circles", timeout=10).json()
    cid = circles[0]["id"]
    photo = _photo()
    digest = hashlib.sha256(photo).hexdigest()
    r = s.post(
        f"{BASE}/api/circles/{cid}/posts",
        data={"content": "pytest照片", "event_date": "2026-09-25"},
        files=[("files", ("t.jpg", photo, "image/jpeg"))],
        timeout=30,
    )
    assert r.status_code == 200
    media_id = r.json()["media"][0]["id"]

    r = s.get(f"{BASE}/api/media/{media_id}/download", timeout=10)
    assert r.status_code == 200
    assert hashlib.sha256(r.content).hexdigest() == digest

    r = s.get(f"{BASE}/api/media/{media_id}/file?variant=preview", timeout=10)
    assert r.status_code == 200
    assert "image" in r.headers.get("content-type", "")

    r = s.get(f"{BASE}/api/media/{media_id}/file?variant=original", timeout=10)
    assert r.status_code == 200
    assert r.headers.get("accept-ranges") == "bytes"


def test_guess_requires_two_photos_and_hides_meta(s):
    s.post(f"{BASE}/api/auth/login", json={"username": "demo_a", "password": "demo1234"}, timeout=10)
    circles = s.get(f"{BASE}/api/circles", timeout=10).json()
    cid = circles[0]["id"]
    r = s.post(f"{BASE}/api/circles/{cid}/albums", json={"title": "PY猜猜", "prompt": "题"}, timeout=10)
    aid = r.json()["id"]
    pool = s.get(f"{BASE}/api/circles/{cid}/albums/{aid}/guess", timeout=10).json()
    assert pool == []

    for i, color in enumerate([(220, 80, 80), (80, 160, 120)]):
        s.post(
            f"{BASE}/api/circles/{cid}/posts",
            data={"content": f"g{i}", "event_date": "2026-09-26", "album_id": str(aid)},
            files=[("files", (f"g{i}.jpg", _photo(color), "image/jpeg"))],
            timeout=30,
        )
    pool = s.get(f"{BASE}/api/circles/{cid}/albums/{aid}/guess", timeout=10).json()
    assert len(pool) >= 2
    assert all("author_nickname" in x and "event_date" in x for x in pool)


def test_timeline_groups_by_event_date(s):
    s.post(f"{BASE}/api/auth/login", json={"username": "demo_a", "password": "demo1234"}, timeout=10)
    circles = s.get(f"{BASE}/api/circles", timeout=10).json()
    cid = circles[0]["id"]
    tl = s.get(f"{BASE}/api/circles/{cid}/timeline", timeout=10).json()
    assert isinstance(tl, list)
    for month in tl:
        assert month["days"]
        for day in month["days"]:
            assert day["event_date"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
