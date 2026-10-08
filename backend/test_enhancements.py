"""Integration checks with disposable accounts/circles, using the running API."""
import hashlib
import io
import os
import uuid
from pathlib import Path

import pytest
import requests
from PIL import Image
from app.database import SessionLocal
from app.models import AuditLog, Circle, Report, User

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001")


def ok(response):
    assert response.ok, response.text
    return response.json()


def photo():
    buffer = io.BytesIO()
    Image.new("RGB", (480, 320), (60, 120, 80)).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def env():
    name = "check_" + uuid.uuid4().hex[:10]
    sessions = []
    for suffix in ("a", "b"):
        session = requests.Session()
        ok(session.post(BASE + "/api/auth/register", json={"username":name+suffix,"password":"testpass1234","nickname":"验证用户"}))
        sessions.append(session)
    circle = ok(sessions[0].post(BASE + "/api/circles", json={"name":name}))
    admin = requests.Session()
    ok(admin.post(BASE+"/api/admin/auth/login",json={"username":"admin","password":"admin123"}))
    yield sessions[0], sessions[1], admin, circle
    db = SessionLocal()
    try:
        # Test-created report records and accounts are removed after circle teardown.
        db.query(Report).filter(Report.circle_id==circle["id"]).delete(synchronize_session=False)
        db.commit()
        sessions[0].delete(BASE+f'/api/circles/{circle["id"]}')
        db.query(User).filter(User.username.in_([name+"a",name+"b"])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def upload(session, circle_id, **extra):
    return ok(session.post(BASE+f"/api/circles/{circle_id}/posts",data={"event_date":"2026-09-30","content":"验证记录",**extra},files=[("files",("photo.jpg",photo(),"image/jpeg"))]))


def join(session, owner, circle):
    request = ok(session.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"]}))
    ok(owner.patch(BASE + f'/api/circles/{circle["id"]}/join-requests/{request["id"]}', json={"status": "approved"}))


def test_user_and_admin_sessions_do_not_overwrite_each_other(env):
    from app.config import settings
    owner, outsider, _, circle = env
    post = upload(owner, circle["id"])
    shared = requests.Session()
    shared.cookies.update(owner.cookies)
    user_cookie = shared.cookies.get(settings.cookie_name)
    owner_id = ok(shared.get(BASE + "/api/auth/me"))["id"]
    admin = ok(shared.post(BASE + "/api/admin/auth/login", json={"username": "admin", "password": "admin123"}))
    assert shared.cookies.get(settings.cookie_name) == user_cookie
    assert ok(shared.get(BASE + "/api/auth/me"))["id"] == owner_id
    assert ok(shared.get(BASE + "/api/admin/auth/me"))["id"] == admin["id"]
    ok(shared.get(BASE + f'/api/posts/{post["id"]}'))
    ok(shared.get(BASE + "/api/admin/stats"))
    media_id = post["media"][0]["id"]
    assert shared.get(BASE + f"/api/admin/media/{media_id}/file?variant=original").content == photo()
    assert owner.get(BASE + "/api/admin/stats").status_code == 401
    assert outsider.get(BASE + f"/api/admin/media/{media_id}/file").status_code == 401
    assert shared.post(BASE + "/api/admin/auth/login", json={"username": "demo_b", "password": "demo1234"}).status_code == 403
    assert shared.cookies.get(settings.cookie_name) == user_cookie
    ok(shared.post(BASE + "/api/admin/auth/logout"))
    assert shared.get(BASE + "/api/admin/stats").status_code == 401
    ok(shared.get(BASE + f'/api/posts/{post["id"]}'))
    ok(shared.post(BASE + "/api/admin/auth/login", json={"username": "admin", "password": "admin123"}))
    admin_token = shared.cookies.get(settings.admin_cookie_name)
    ok(shared.post(BASE + "/api/auth/logout"))
    assert shared.get(BASE + "/api/auth/me").status_code == 401
    ok(shared.get(BASE + "/api/admin/stats"))
    impostor = requests.Session()
    impostor.cookies.set(settings.cookie_name, admin_token)
    assert impostor.get(BASE + "/api/auth/me").status_code == 401


def test_report_permissions_idempotency_and_retention(env):
    owner, outsider, admin, circle = env
    post = upload(owner,circle["id"])
    endpoint = BASE+f'/api/posts/{post["id"]}/reports'
    assert outsider.post(endpoint,json={"report_type":"隐私侵权"}).status_code==403
    assert owner.post(endpoint,json={"report_type":"其他","reason":" "}).status_code==400
    assert owner.post(endpoint,json={"report_type":"其他","reason":"x"*1001}).status_code==422
    assert owner.post(endpoint,json={"report_type":"无效"}).status_code==422
    first=ok(owner.post(endpoint,json={"report_type":"隐私侵权","reason":"验证"}))
    duplicate=ok(owner.post(endpoint,json={"report_type":"隐私侵权","reason":"验证"}))
    assert first["id"]==duplicate["id"]
    reports=ok(admin.get(BASE+"/api/admin/reports",params={"status":"all"}))
    assert next(r for r in reports if r["id"]==first["id"])["media"][0]["id"]==post["media"][0]["id"]
    ok(admin.post(BASE+f'/api/admin/reports/{first["id"]}/remove',json={"reason":"测试验证"}))
    retained=next(r for r in ok(admin.get(BASE+"/api/admin/reports",params={"status":"all"})) if r["id"]==first["id"])
    assert retained["status"]=="removed" and retained["post_deleted"]
    assert retained["post_id"]==post["id"] and retained["content"]=="验证记录" and retained["media"]==[]
    assert owner.get(BASE+post["media"][0]["original_url"]).status_code==404


def test_branches_albums_location_and_record_edits(env):
    owner, outsider, admin, circle = env
    prefix=BASE+f'/api/circles/{circle["id"]}'
    main=ok(owner.post(prefix+"/lines",json={"title":"旅行","kind":"travel"}))["id"]
    child=ok(owner.post(prefix+"/lines",json={"title":"云南","kind":"travel","parent_id":main}))["id"]
    assert outsider.get(prefix+"/lines").status_code==403
    assert owner.patch(prefix+f"/lines/{main}",json={"title":"旅行","parent_id":child}).status_code==400
    album=ok(owner.post(prefix+"/albums",json={"title":"云南分册","line_id":child}))
    post=upload(owner,circle["id"],album_id=album["id"],latitude="25.6065",longitude="100.2676",location_name="大理")
    assert post["line_id"]==child
    timeline=ok(owner.get(prefix+"/timeline",params={"line_id":main}))
    assert timeline[0]["days"][0]["posts"][0]["id"]==post["id"]
    edited=ok(owner.patch(BASE+f'/api/posts/{post["id"]}',json={"content":"编辑后的回忆","event_date":"2025-08-02","latitude":31.2304,"longitude":121.4737,"location_name":"上海"}))
    assert edited["content"]=="编辑后的回忆" and edited["latitude"]==31.2304
    assert outsider.patch(BASE+f'/api/posts/{post["id"]}',json={"content":"越权"}).status_code==403
    assert owner.patch(BASE+f'/api/posts/{post["id"]}',json={"latitude":None}).status_code==400
    ok(owner.delete(prefix+f"/lines/{main}"))
    assert next(l for l in ok(owner.get(prefix+"/lines")) if l["id"]==child)["parent_id"] is None
    ok(owner.delete(prefix+f'/albums/{album["id"]}'))
    assert ok(owner.get(BASE+f'/api/posts/{post["id"]}'))["album_id"] is None
    assert hashlib.sha256(owner.get(BASE+post["media"][0]["download_url"]).content).hexdigest()==post["media"][0]["sha256"]


def test_failed_upload_cleans_originals_and_previews(env):
    owner, _, _, circle=env
    folders=[Path("uploads/photos"),Path("uploads/previews"),Path("uploads/tmp")]
    before={p.resolve() for f in folders for p in f.iterdir()}
    response=owner.post(BASE+f'/api/circles/{circle["id"]}/posts',data={"event_date":"2026-09-30"},files=[("files",("good.jpg",photo(),"image/jpeg")),("files",("bad.jpg",b"not a photo","image/jpeg"))])
    assert response.status_code==400,response.text
    assert {p.resolve() for f in folders for p in f.iterdir()}==before
    assert ok(owner.get(BASE+f'/api/circles/{circle["id"]}/posts'))==[]
    assert ok(owner.get(BASE + "/api/me/timeline", params={"kind": "post"}))["total"] == 0


def test_circle_delete_cleans_media_and_rejects_non_owner(env):
    owner, member, _, circle=env
    join(member, owner, circle)
    post=upload(owner,circle["id"])
    assert member.delete(BASE+f'/api/circles/{circle["id"]}').status_code==403
    ok(owner.delete(BASE+f'/api/circles/{circle["id"]}'))
    assert owner.get(BASE+post["media"][0]["original_url"]).status_code==404


def test_real_video_range_and_download(env):
    owner, _, _, circle=env
    source=Path(__file__).parent.parent / "tests/fixtures/flower.mp4"
    content=source.read_bytes()
    post=ok(owner.post(BASE+f'/api/circles/{circle["id"]}/posts',data={"event_date":"2026-10-01","content":"视频验证"},files=[("files",("flower.mp4",content,"video/mp4"))]))
    media=post["media"][0]
    for header,expected in [("bytes=0-99",content[:100]),("bytes=100-",content[100:]),("bytes=-50",content[-50:])]:
        response=owner.get(BASE+media["original_url"],headers={"Range":header})
        assert response.status_code==206 and response.content==expected
        assert response.headers["Accept-Ranges"]=="bytes"
    for header in ["bytes=-0","bytes=9-4",f"bytes={len(content)}-","bytes=0-10,20-30","bytes=-"]:
        response=owner.get(BASE+media["original_url"],headers={"Range":header})
        assert response.status_code==416 and response.headers["Content-Range"]==f"bytes */{len(content)}"
    assert owner.get(BASE+media["download_url"]).content==content


def test_personal_timeline_operations_and_retention(env):
    owner, member, _, circle = env
    endpoint = BASE + "/api/me/timeline"
    assert requests.get(endpoint).status_code == 401
    assert ok(member.get(endpoint))["items"] == []
    assert ok(member.get(endpoint, params={"circle_id": circle["id"]}))["total"] == 0
    assert member.patch(BASE + f'/api/circles/{circle["id"]}/settings', json={"name": "越权"}).status_code == 403
    assert ok(member.get(endpoint))["total"] == 0
    join(member, owner, circle)
    post = upload(owner, circle["id"], event_date="2025-08-02")
    member_post = upload(member, circle["id"])
    ok(owner.patch(BASE + f'/api/posts/{post["id"]}', json={"content": "编辑"}))
    initial = ok(owner.get(endpoint))
    assert [e["action"] for e in initial["items"]] == ["post_edit", "post_create", "join_review", "circle_create"]
    assert all(e["target_id"] != member_post["id"] for e in initial["items"] if e["target_kind"] == "post")
    assert all(e["can_open_post"] for e in initial["items"] if e["post_id"])
    assert ok(owner.get(endpoint, params={"year": 2025}))["total"] == 0
    assert ok(owner.get(endpoint, params={"year": post["created_at"][:4], "kind": "post"}))["total"] == 2
    for kind, path in [("album", "albums"), ("line", "lines")]:
        prefix = BASE + f'/api/circles/{circle["id"]}/{path}'
        created = ok(owner.post(prefix, json={"title": "操作验证"}))
        ok(owner.patch(prefix + f'/{created["id"]}', json={"title": "修改名称"}))
        ok(owner.delete(prefix + f'/{created["id"]}'))
        assert {e["action"] for e in ok(owner.get(endpoint, params={"kind": kind}))["items"]} == {f"{kind}_create", f"{kind}_edit", f"{kind}_delete"}
    comment = ok(owner.post(BASE + f'/api/posts/{post["id"]}/comments', json={"content": "评论验证"}))
    ok(owner.delete(BASE + f'/api/comments/{comment["id"]}'))
    for _ in range(2):
        ok(owner.post(BASE + f'/api/posts/{post["id"]}/reports', json={"report_type": "隐私侵权"}))
    assert ok(owner.get(endpoint, params={"kind": "report"}))["total"] == 1
    ok(owner.delete(BASE + f'/api/posts/{post["id"]}'))
    remaining = ok(owner.get(endpoint))
    assert all(not e["can_open_post"] for e in remaining["items"] if e["post_id"] == post["id"])
    assert any(e["action"] == "post_delete" for e in remaining["items"])
    user = ok(member.get(BASE + "/api/auth/me"))
    ok(member.delete(BASE + f'/api/circles/{circle["id"]}/members/{user["id"]}'))
    assert {e["action"] for e in ok(member.get(endpoint))["items"]} == {"circle_apply", "circle_join", "post_create", "circle_leave"}
    assert all(not e["can_open_post"] for e in ok(member.get(endpoint))["items"])
    ok(owner.delete(BASE + f'/api/circles/{circle["id"]}'))
    history = ok(owner.get(endpoint))
    assert history["items"][0]["action"] == "circle_delete"
    assert history["circles"][0]["name"] == circle["name"]
    first = ok(owner.get(endpoint, params={"limit": 2}))["items"]
    second = ok(owner.get(endpoint, params={"limit": 2, "offset": 2}))["items"]
    assert [e["id"] for e in first + second] == [e["id"] for e in history["items"][:4]]
    cursor_page = ok(owner.get(endpoint, params={"limit": 2, "before_id": first[-1]["id"]}))["items"]
    assert [e["id"] for e in cursor_page] == [e["id"] for e in second]
    assert member.get(endpoint, params={"before_id": first[0]["id"]}).status_code == 400
    assert all(not e["can_open_post"] for e in history["items"])
