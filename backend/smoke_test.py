"""后端接口冒烟：注册/登录 → 建圈 → 发帖（合成图）→ 相册 → 下载原图哈希一致。"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image

BASE = "http://127.0.0.1:8000"


def main() -> int:
    s = requests.Session()
    r = s.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200, r.text
    print("health ok")

    # login demo_a
    r = s.post(f"{BASE}/api/auth/login", json={"username": "demo_a", "password": "demo1234"}, timeout=10)
    assert r.status_code == 200, r.text
    print("login ok", r.json()["username"])

    r = s.get(f"{BASE}/api/circles", timeout=10)
    assert r.status_code == 200, r.text
    circles = r.json()
    assert circles, "no circles"
    cid = circles[0]["id"]
    print("circles ok", [(c["id"], c["name"], c["invite_code"]) for c in circles])

    # create album
    r = s.post(
        f"{BASE}/api/circles/{cid}/albums",
        json={"title": "冒烟测试分册", "prompt": "拍一张今天"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    album_id = r.json()["id"]
    print("album ok", album_id)

    # synthesize photo
    img = Image.new("RGB", (800, 600), (224, 122, 95))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    photo_bytes = buf.getvalue()
    photo_hash = hashlib.sha256(photo_bytes).hexdigest()

    r = s.post(
        f"{BASE}/api/circles/{cid}/posts",
        data={
            "content": "冒烟测试的一条痕迹",
            "event_date": "2026-09-20",
            "activity_tag": "日常",
            "album_id": str(album_id),
        },
        files=[("files", ("smoke.jpg", photo_bytes, "image/jpeg"))],
        timeout=30,
    )
    assert r.status_code == 200, r.text
    post = r.json()
    print("post ok", post["id"], "media", [(m["id"], m["kind"], m["sha256"][:12]) for m in post["media"]])
    media_id = post["media"][0]["id"]

    # download original and compare hash
    r = s.get(f"{BASE}/api/media/{media_id}/download", timeout=10)
    assert r.status_code == 200, r.status_code
    dl_hash = hashlib.sha256(r.content).hexdigest()
    assert dl_hash == photo_hash, f"hash mismatch {dl_hash} vs {photo_hash}"
    print("export original hash match", dl_hash[:16])

    # preview
    r = s.get(f"{BASE}/api/media/{media_id}/file?variant=preview", timeout=10)
    assert r.status_code == 200, r.status_code
    print("preview ok", len(r.content))

    # timeline
    r = s.get(f"{BASE}/api/circles/{cid}/timeline", timeout=10)
    assert r.status_code == 200, r.text
    print("timeline months", len(r.json()))

    # shared album
    r = s.get(f"{BASE}/api/circles/{cid}/album", timeout=10)
    assert r.status_code == 200, r.text
    print("shared album items", len(r.json()))

    # guess pool
    r = s.get(f"{BASE}/api/circles/{cid}/albums/{album_id}/guess", timeout=10)
    assert r.status_code == 200, r.text
    print("guess pool", len(r.json()))

    # comments
    r = s.post(f"{BASE}/api/posts/{post['id']}/comments", json={"content": "好看"}, timeout=10)
    assert r.status_code == 200, r.text
    print("comment ok")

    print("\nALL SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("SMOKE FAILED:", e)
        sys.exit(1)
