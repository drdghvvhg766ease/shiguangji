"""Circle activity tags: list / add / rename / delete and permission boundaries."""
import uuid

import pytest
import requests

from app.database import SessionLocal
from app.models import Circle, User
from test_enhancements import BASE, ok, upload


@pytest.fixture
def tags_env():
    prefix = "tags_" + uuid.uuid4().hex[:8]
    owner, member = requests.Session(), requests.Session()
    users = []
    for session, suffix in ((owner, "a"), (member, "b")):
        users.append(
            ok(
                session.post(
                    BASE + "/api/auth/register",
                    json={
                        "username": prefix + suffix,
                        "password": "testpass1234",
                        "nickname": f"标签成员{suffix}",
                    },
                )
            )
        )
    circle = ok(owner.post(BASE + "/api/circles", json={"name": prefix}))
    joined = ok(member.post(BASE + "/api/circles/join", json={"invite_code": circle["invite_code"]}))
    ok(
        owner.patch(
            BASE + f'/api/circles/{circle["id"]}/join-requests/{joined["id"]}',
            json={"status": "approved"},
        )
    )
    admin = requests.Session()
    ok(admin.post(BASE + "/api/admin/auth/login", json={"username": "admin", "password": "admin123"}))
    yield owner, member, circle, users, admin
    db = SessionLocal()
    try:
        if db.get(Circle, circle["id"]):
            ok(owner.delete(BASE + f'/api/circles/{circle["id"]}'))
        for user in users:
            ok(admin.delete(BASE + f'/api/admin/users/{user["id"]}', json={"reason": "标签功能验证账号清理"}))
    finally:
        db.close()


def by_name(tags, name):
    return next((tag for tag in tags if tag["name"] == name), None)


def test_tag_crud_syncs_records(tags_env):
    owner, member, circle, _, _ = tags_env
    base = BASE + f'/api/circles/{circle["id"]}/tags'

    post = upload(owner, circle["id"], activity_tag="露营")
    assert post["activity_tag"] == "露营"

    tags = ok(owner.get(base))
    assert by_name(tags, "日常") is not None
    assert by_name(tags, "露营")["post_count"] == 1
    assert ok(member.get(base))  # 普通成员可读

    added = ok(owner.post(base, json={"name": "露营日记"}))
    assert by_name(added, "露营日记")["post_count"] == 0
    assert owner.post(base, json={"name": "日常"}).status_code == 409
    assert owner.post(base, json={"name": "   "}).status_code == 400

    camping = by_name(tags, "露营")
    renamed = ok(owner.patch(f'{base}/{camping["id"]}', json={"name": "户外露营"}))
    assert by_name(renamed, "露营") is None
    assert by_name(renamed, "户外露营")["post_count"] == 1
    detail = ok(owner.get(BASE + f'/api/posts/{post["id"]}'))
    assert detail["activity_tag"] == "户外露营"

    removed = by_name(renamed, "户外露营")
    after = ok(owner.delete(f'{base}/{removed["id"]}'))
    assert by_name(after, "户外露营") is None
    detail = ok(owner.get(BASE + f'/api/posts/{post["id"]}'))
    assert detail["activity_tag"] == "日常"

    for tag in ok(owner.get(base)):
        if tag["name"] != "日常":
            ok(owner.delete(f'{base}/{tag["id"]}'))
    only = ok(owner.get(base))
    assert [tag["name"] for tag in only] == ["日常"]
    assert owner.delete(f'{base}/{only[0]["id"]}').status_code == 400


def test_tag_management_open_to_members(tags_env):
    owner, member, circle, _, admin = tags_env
    base = BASE + f'/api/circles/{circle["id"]}/tags'
    tags = ok(owner.get(base))
    daily = by_name(tags, "日常")
    assert daily is not None

    # 普通成员也能新增 / 改名 / 删除
    added = ok(member.post(base, json={"name": "成员也能加"}))
    created = by_name(added, "成员也能加")
    assert created is not None
    renamed = ok(member.patch(f'{base}/{created["id"]}', json={"name": "成员改的名"}))
    assert by_name(renamed, "成员改的名") is not None
    after = ok(member.delete(f'{base}/{created["id"]}'))
    assert by_name(after, "成员改的名") is None

    assert owner.delete(f'{base}/999999').status_code == 404

    # 不在圈子里的人读写都不行
    outsider = requests.Session()
    stranger = ok(
        outsider.post(
            BASE + "/api/auth/register",
            json={"username": "tags_out_" + uuid.uuid4().hex[:8], "password": "testpass1234"},
        )
    )
    try:
        assert outsider.get(base).status_code == 403
        assert outsider.post(base, json={"name": "圈外人"}).status_code == 403
        assert outsider.patch(f'{base}/{daily["id"]}', json={"name": "圈外改名"}).status_code == 403
    finally:
        ok(admin.delete(BASE + f'/api/admin/users/{stranger["id"]}', json={"reason": "标签功能验证账号清理"}))
