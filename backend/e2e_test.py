"""端到端：双账号 · 入圈 · 权限 · 导出哈希 · 非成员拒绝。"""
from __future__ import annotations

import hashlib
import io
import sys

import requests
from PIL import Image

BASE = "http://127.0.0.1:8000"


def make_photo(color, size=(640, 480)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def main() -> int:
    sa, sb, sc = requests.Session(), requests.Session(), requests.Session()

    # C is outsider
    for s, name, nick in ((sa, "e2e_a", "小A"), (sb, "e2e_b", "小B"), (sc, "e2e_c", "路人C")):
        r = s.post(
            f"{BASE}/api/auth/register",
            json={"username": name, "password": "pass1234", "nickname": nick},
            timeout=10,
        )
        if r.status_code == 400 and "占用" in r.text:
            r = s.post(
                f"{BASE}/api/auth/login",
                json={"username": name, "password": "pass1234"},
                timeout=10,
            )
        assert r.status_code == 200, f"{name}: {r.text}"
        print(f"auth {name} ok")

    # A creates circle
    r = sa.post(
        f"{BASE}/api/circles",
        json={"name": "E2E小队", "description": "端到端测试"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    circle = r.json()
    cid, code = circle["id"], circle["invite_code"]
    print("circle", cid, "invite", code)
    assert circle["is_owner"]

    # B joins
    r = sb.post(f"{BASE}/api/circles/join", json={"invite_code": code}, timeout=10)
    assert r.status_code == 200, r.text
    print("B joined")

    # C cannot see posts
    r = sc.get(f"{BASE}/api/circles/{cid}/posts", timeout=10)
    assert r.status_code == 403, r.text
    print("C blocked from posts")

    # A uploads photo
    photo = make_photo((224, 122, 95))
    digest = hashlib.sha256(photo).hexdigest()
    r = sa.post(
        f"{BASE}/api/circles/{cid}/posts",
        data={"content": "E2E照片", "event_date": "2026-09-21", "activity_tag": "旅行"},
        files=[("files", ("e2e.jpg", photo, "image/jpeg"))],
        timeout=30,
    )
    assert r.status_code == 200, r.text
    post = r.json()
    mid = post["media"][0]["id"]
    print("post", post["id"], "media", mid)

    # B can download original, hash matches
    r = sb.get(f"{BASE}/api/media/{mid}/download", timeout=10)
    assert r.status_code == 200
    assert hashlib.sha256(r.content).hexdigest() == digest
    print("B export hash OK")

    # C cannot download
    r = sc.get(f"{BASE}/api/media/{mid}/download", timeout=10)
    assert r.status_code == 403, r.status_code
    print("C blocked from download")

    # B cannot edit A's post
    r = sb.patch(f"{BASE}/api/posts/{post['id']}", json={"content": "hack"}, timeout=10)
    assert r.status_code == 403
    print("B cannot edit A post")

    # A can edit
    r = sa.patch(
        f"{BASE}/api/posts/{post['id']}",
        json={"content": "改过的文字", "activity_tag": "毕业"},
        timeout=10,
    )
    assert r.status_code == 200 and r.json()["content"] == "改过的文字"
    print("A edit ok")

    # album + guess
    r = sa.post(
        f"{BASE}/api/circles/{cid}/albums",
        json={"title": "E2E分册", "prompt": "拍一张今天"},
        timeout=10,
    )
    album_id = r.json()["id"]

    photo2 = make_photo((129, 178, 154))
    r = sb.post(
        f"{BASE}/api/circles/{cid}/posts",
        data={"content": "B的贡献", "event_date": "2026-09-22", "album_id": str(album_id)},
        files=[("files", ("e2e2.jpg", photo2, "image/jpeg"))],
        timeout=30,
    )
    assert r.status_code == 200, r.text

    # assign A's post to album
    r = sa.patch(f"{BASE}/api/posts/{post['id']}", json={"album_id": album_id}, timeout=10)
    assert r.status_code == 200

    r = sa.get(f"{BASE}/api/circles/{cid}/albums/{album_id}/guess", timeout=10)
    assert r.status_code == 200
    pool = r.json()
    assert len(pool) >= 2, pool
    print("guess pool", len(pool))

    # collage thumbs
    r = sa.get(f"{BASE}/api/circles/{cid}/albums", timeout=10)
    albums = r.json()
    target = next(a for a in albums if a["id"] == album_id)
    print("cover thumbs", target["cover_thumbs"], "posts", target["post_count"], "people", target["participant_count"])
    assert target["participant_count"] == 2

    # timeline
    r = sa.get(f"{BASE}/api/circles/{cid}/timeline", timeout=10)
    assert r.status_code == 200 and r.json()
    print("timeline ok")

    # rotate invite, old code fails
    r = sa.post(f"{BASE}/api/circles/{cid}/invite-code/rotate", timeout=10)
    new_code = r.json()["invite_code"]
    assert new_code != code
    r = sb.post(f"{BASE}/api/circles/join", json={"invite_code": code}, timeout=10)
    assert r.status_code == 404
    print("old invite rejected")

    # comment delete by author
    r = sb.post(f"{BASE}/api/posts/{post['id']}/comments", json={"content": "赞"}, timeout=10)
    c_id = r.json()["id"]
    r = sc.delete(f"{BASE}/api/comments/{c_id}", timeout=10)
    assert r.status_code == 403
    r = sb.delete(f"{BASE}/api/comments/{c_id}", timeout=10)
    assert r.status_code == 200
    print("comment perms ok")

    # B leaves
    r = sb.delete(f"{BASE}/api/circles/{cid}/members/{sb.get(f'{BASE}/api/auth/me').json()['id']}", timeout=10)
    assert r.status_code == 200
    print("B left")

    # B cannot read after leave
    r = sb.get(f"{BASE}/api/circles/{cid}/posts", timeout=10)
    assert r.status_code == 403
    print("B blocked after leave")

    print("\nALL E2E TESTS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback

        traceback.print_exc()
        print("E2E FAILED:", e)
        sys.exit(1)
