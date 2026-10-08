"""Social workflows use isolated users and circles on the running local API."""
import io
import uuid
from pathlib import Path

import pytest
import requests
from PIL import Image
from app.database import SessionLocal
from app.models import Circle, User
from test_enhancements import BASE, ok, photo, upload


@pytest.fixture
def social():
    users, sessions = [], []
    prefix = "social_" + uuid.uuid4().hex[:8]
    for index in range(4):
        session = requests.Session()
        users.append(ok(session.post(BASE + "/api/auth/register", json={"username": prefix + str(index), "password": "testpass1234", "nickname": f"验证成员{index}"})))
        sessions.append(session)
    circle = ok(sessions[0].post(BASE + "/api/circles", json={"name": prefix}))
    circles = [circle["id"]]
    admin = requests.Session()
    ok(admin.post(BASE + "/api/admin/auth/login", json={"username": "admin", "password": "admin123"}))
    yield sessions, users, circle, circles, admin
    db = SessionLocal()
    try:
        for cid in circles:
            item = db.get(Circle, cid)
            if item:
                owner = next(s for s, u in zip(sessions, users) if u["id"] == item.owner_id)
                ok(owner.delete(BASE + f"/api/circles/{cid}"))
        for user in users:
            ok(admin.delete(BASE + f'/api/admin/users/{user["id"]}', json={"reason": "独立功能验证账号清理"}))
    finally:
        db.close()


def approve(owner, applicant, circle):
    request = ok(applicant.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"], "message": "朋友邀请"}))
    ok(owner.patch(BASE + f'/api/circles/{circle["id"]}/join-requests/{request["id"]}', json={"status": "approved"}))
    return request


def test_join_review_roles_and_permission_boundaries(social):
    sessions, users, circle, _, admin = social
    owner, manager, member, outsider = sessions
    prefix = BASE + f'/api/circles/{circle["id"]}'
    first = ok(manager.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"]}))
    assert first == ok(manager.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"]}))
    assert ok(manager.get(BASE + "/api/circles")) == []
    assert manager.get(prefix + "/posts").status_code == 403
    assert manager.patch(prefix + f'/join-requests/{first["id"]}', json={"status": "approved"}).status_code == 403
    ok(owner.patch(prefix + f'/join-requests/{first["id"]}', json={"status": "approved"}))
    ok(owner.patch(prefix + f'/members/{users[1]["id"]}/role', json={"role": "admin"}))
    assert ok(manager.get(BASE + "/api/circles"))[0]["can_manage"]
    approve(manager, member, circle)
    assert member.patch(prefix + f'/members/{users[1]["id"]}/role', json={"role": "member"}).status_code == 403
    assert manager.patch(prefix + f'/members/{users[2]["id"]}/role', json={"role": "admin"}).status_code == 403
    assert manager.delete(prefix).status_code == 403
    assert manager.delete(prefix + f'/members/{users[0]["id"]}').status_code == 400
    own_post = upload(member, circle["id"])
    assert manager.patch(BASE + f'/api/posts/{own_post["id"]}', json={"content": "禁止修改他人正文"}).status_code == 403
    ok(manager.delete(BASE + f'/api/posts/{own_post["id"]}'))
    album = ok(member.post(prefix + "/albums", json={"title": "普通成员分册"}))
    line = ok(member.post(prefix + "/lines", json={"title": "普通成员分支"}))
    assert outsider.patch(prefix + f'/albums/{album["id"]}', json={"title": "越权"}).status_code == 403
    ok(manager.patch(prefix + f'/albums/{album["id"]}', json={"title": "管理员编辑"}))
    ok(manager.delete(prefix + f'/lines/{line["id"]}'))
    ok(owner.patch(prefix + f'/members/{users[2]["id"]}/role', json={"role": "admin"}))
    assert manager.delete(prefix + f'/members/{users[2]["id"]}').status_code == 403
    ok(owner.patch(prefix + f'/members/{users[2]["id"]}/role', json={"role": "member"}))
    retained = upload(member, circle["id"])
    ok(manager.delete(prefix + f'/members/{users[2]["id"]}'))
    assert any(p["id"] == retained["id"] for p in ok(owner.get(prefix + "/posts")))
    retry = ok(member.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"]}))
    rejected = ok(manager.patch(prefix + f'/join-requests/{retry["id"]}', json={"status": "rejected", "reason": "稍后再加入"}))
    assert rejected["status"] == "rejected"
    assert ok(member.get(BASE + "/api/circles/join-requests/mine"))[0]["review_reason"] == "稍后再加入"
    assert member.get(prefix + "/posts").status_code == 403
    approve(owner, member, circle)
    assert any(p["id"] == retained["id"] for p in ok(member.get(prefix + "/posts")))
    ok(owner.post(prefix + "/transfer", json={"user_id": users[1]["id"]}))
    assert ok(manager.get(BASE + "/api/circles"))[0]["role"] == "owner"
    assert ok(owner.get(BASE + "/api/circles"))[0]["role"] == "member"


def test_profile_avatar_password_and_session_invalidation(social):
    sessions, users, _, _, _ = social
    user = sessions[3]
    changed = ok(user.patch(BASE + "/api/auth/profile", json={"nickname": "新的名字"}))
    assert changed["nickname"] == "新的名字"
    assert user.patch(BASE + "/api/auth/profile", json={"nickname": " "}).status_code == 400
    assert user.post(BASE + "/api/auth/avatar", files={"file": ("bad.jpg", b"invalid", "image/jpeg")}).status_code == 400
    avatar = ok(user.post(BASE + "/api/auth/avatar", files={"file": ("avatar.jpg", photo(), "image/jpeg")}))
    assert avatar["avatar"].startswith("/api/auth/users/")
    image = Image.open(io.BytesIO(user.get(BASE + avatar["avatar"]).content))
    assert image.size == (256, 256)
    db = SessionLocal()
    first = db.get(User, users[3]["id"]).avatar
    db.close()
    ok(user.post(BASE + "/api/auth/avatar", files={"file": ("avatar.jpg", photo(), "image/jpeg")}))
    assert not (Path(__file__).parent / "uploads" / first).exists()
    old_session = requests.Session()
    ok(old_session.post(BASE + "/api/auth/login", json={"username": users[3]["username"], "password": "testpass1234"}))
    assert user.post(BASE + "/api/auth/password", json={"current_password": "wrong", "new_password": "newpass1234"}).status_code == 400
    ok(user.post(BASE + "/api/auth/password", json={"current_password": "testpass1234", "new_password": "newpass1234"}))
    assert user.get(BASE + "/api/auth/me").status_code == 200
    assert old_session.get(BASE + "/api/auth/me").status_code == 401
    assert old_session.post(BASE + "/api/auth/login", json={"username": users[3]["username"], "password": "testpass1234"}).status_code == 401
    ok(old_session.post(BASE + "/api/auth/login", json={"username": users[3]["username"], "password": "newpass1234"}))


def test_messages_likes_replies_announcements_and_report_feedback(social):
    sessions, users, circle, _, admin = social
    owner, member, outsider, _ = sessions
    approve(owner, member, circle)
    prefix = BASE + f'/api/circles/{circle["id"]}'
    post = upload(owner, circle["id"])
    like = ok(member.put(BASE + f'/api/posts/{post["id"]}/like'))
    assert like == ok(member.put(BASE + f'/api/posts/{post["id"]}/like'))
    assert like["like_count"] == 1
    assert ok(member.get(BASE + f'/api/posts/{post["id"]}'))["liked"]
    comment = ok(member.post(BASE + f'/api/posts/{post["id"]}/comments', json={"content": "好看的回忆"}))
    reply = ok(owner.post(BASE + f'/api/posts/{post["id"]}/comments', json={"content": "谢谢", "reply_to_id": comment["id"]}))
    assert reply["reply_to_name"] == users[1]["nickname"]
    assert owner.post(BASE + f'/api/posts/{post["id"]}/comments', json={"content": "错配回复", "reply_to_id": 999999}).status_code == 400
    assert member.post(prefix + "/announcements", json={"title": "越权", "content": "禁止"}).status_code == 403
    notice = ok(owner.post(prefix + "/announcements", json={"title": "周末见", "content": "一起拍照"}))
    assert len(ok(member.get(prefix + "/announcements"))) == 1
    assert outsider.get(prefix + "/announcements").status_code == 403
    report = ok(member.post(BASE + f'/api/posts/{post["id"]}/reports', json={"report_type": "隐私侵权"}))
    ok(admin.post(BASE + f'/api/admin/reports/{report["id"]}/dismiss', json={"reason": "未发现违规"}))
    inbox = ok(member.get(BASE + "/api/me/notifications"))
    assert {m["kind"] for m in inbox["items"]} >= {"join_result", "comment", "announcement", "report_result"}
    message_id = inbox["items"][0]["id"]
    assert outsider.put(BASE + f"/api/me/notifications/{message_id}/read").status_code == 404
    ok(member.put(BASE + "/api/me/notifications/read-all"))
    assert ok(member.get(BASE + "/api/me/notifications"))["unread_count"] == 0
    assert ok(member.delete(BASE + f'/api/posts/{post["id"]}/like'))["like_count"] == 0
    ok(owner.delete(prefix + f'/announcements/{notice["id"]}'))


def test_folders_sharing_access_and_deleted_record_placeholders(social):
    sessions, users, circle, circles, _ = social
    owner, member, outsider, _ = sessions
    approve(owner, member, circle)
    other = ok(owner.post(BASE + "/api/circles", json={"name": "仅圈主参加的另一个圈子"}))
    circles.append(other["id"])
    first = upload(owner, circle["id"])
    secret = upload(owner, other["id"])
    private = ok(owner.post(BASE + "/api/me/favorite-folders", json={"title": "私密分类"}))
    shared = ok(owner.post(BASE + "/api/me/favorite-folders", json={"title": "共享分类", "share_circle_ids": [circle["id"]]}))
    for post in (first, secret):
        saved = ok(owner.put(BASE + f'/api/me/favorite-folders/{shared["id"]}/items', json={"post_id": post["id"]}))
        assert saved == ok(owner.put(BASE + f'/api/me/favorite-folders/{shared["id"]}/items', json={"post_id": post["id"]}))
    assert member.get(BASE + f'/api/me/favorite-folders/{private["id"]}/items').status_code == 404
    assert outsider.get(BASE + f'/api/me/favorite-folders/{shared["id"]}/items').status_code == 404
    assert member.patch(BASE + f'/api/me/favorite-folders/{shared["id"]}', json={"title": "越权"}).status_code == 404
    records = ok(member.get(BASE + f'/api/me/favorite-folders/{shared["id"]}/items'))["items"]
    assert next(i for i in records if i["post_id"] == secret["id"])["post"] is None
    assert next(i for i in records if i["post_id"] == first["id"])["post"]["id"] == first["id"]
    assert member.post(BASE + "/api/me/favorite-folders", json={"title": "越权分享", "share_circle_ids": [other["id"]]}).status_code == 403
    ok(owner.delete(BASE + f'/api/posts/{first["id"]}'))
    records = ok(owner.get(BASE + f'/api/me/favorite-folders/{shared["id"]}/items'))["items"]
    assert next(i for i in records if i["post_id"] == first["id"])["post"] is None
    ok(member.delete(BASE + f'/api/circles/{circle["id"]}/members/{users[1]["id"]}'))
    assert member.get(BASE + f'/api/me/favorite-folders/{shared["id"]}/items').status_code == 404
    ok(owner.delete(BASE + f'/api/me/favorite-folders/{shared["id"]}'))
    assert owner.get(BASE + f'/api/posts/{secret["id"]}').status_code == 200
