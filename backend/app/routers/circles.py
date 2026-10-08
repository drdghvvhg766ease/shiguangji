from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..activity import record_activity
from ..models import Announcement, Circle, CircleMember, JoinRequest, Media, Post, User
from ..notifications import notify
from ..profiles import avatar_url
from ..media_utils import absolute_from_upload, cleanup
from ..schemas import (
    CircleCreate,
    CircleJoin,
    CircleOut,
    CircleSettingsIn,
    CircleTransferIn,
    MemberOut,
    AnnouncementIn, JoinReview, RoleUpdate,
)
from ..security import get_current_user, is_circle_manager, is_circle_owner, require_circle_member

router = APIRouter(prefix="/api/circles", tags=["circles"])


def _invite_code() -> str:
    return secrets.token_hex(4).upper()


def _circle_out(circle: Circle, user_id: int, member_count: int, role="member") -> CircleOut:
    return CircleOut(
        id=circle.id,
        name=circle.name,
        description=circle.description,
        cover_color=circle.cover_color,
        invite_code=circle.invite_code,
        owner_id=circle.owner_id,
        allow_member_invite=circle.allow_member_invite,
        created_at=circle.created_at,
        member_count=member_count,
        is_owner=circle.owner_id == user_id,
        role="owner" if circle.owner_id == user_id else role,
        can_manage=circle.owner_id == user_id or role == "admin",
    )


@router.get("", response_model=list[CircleOut])
def list_my_circles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Circle, CircleMember)
        .join(CircleMember, CircleMember.circle_id == Circle.id)
        .filter(CircleMember.user_id == user.id)
        .order_by(Circle.created_at.desc())
        .all()
    )
    result = []
    for circle, _m in rows:
        count = db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count()
        result.append(_circle_out(circle, user.id, count, _m.role))
    return result


@router.post("", response_model=CircleOut)
def create_circle(
    data: CircleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle = Circle(
        name=data.name.strip(),
        description=data.description.strip() or None,
        cover_color=data.cover_color,
        invite_code=_invite_code(),
        owner_id=user.id,
        allow_member_invite=True,
    )
    db.add(circle)
    db.flush()
    db.add(CircleMember(circle_id=circle.id, user_id=user.id))
    record_activity(db, user.id, circle.id, "circle_create", "circle", circle.id, circle.name)
    db.commit()
    db.refresh(circle)
    return _circle_out(circle, user.id, 1)


@router.post("/join")
def join_circle(
    data: CircleJoin,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle = db.query(Circle).filter(Circle.invite_code == data.invite_code.strip().upper()).with_for_update().first()
    if not circle:
        raise HTTPException(status_code=404, detail="邀请码无效")
    exists = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == circle.id, CircleMember.user_id == user.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="你已在该圈子中")
    request = db.query(JoinRequest).filter_by(circle_id=circle.id, user_id=user.id).first()
    if request and request.status == "pending":
        return {"id": request.id, "circle_id": circle.id, "circle_name": circle.name, "status": "pending"}
    if request:
        request.status, request.message = "pending", data.message.strip()
        request.review_reason, request.reviewed_by, request.reviewed_at = "", None, None
        request.created_at = datetime.now()
    else:
        request = JoinRequest(circle_id=circle.id, user_id=user.id, message=data.message.strip())
        db.add(request)
    db.flush()
    managers = [uid for (uid,) in db.query(CircleMember.user_id).filter(CircleMember.circle_id == circle.id, CircleMember.role == "admin")]
    notify(db, managers + [circle.owner_id], "join_request", "新的入圈申请", f"{user.nickname} 申请加入 {circle.name}", circle.id)
    record_activity(db, user.id, circle.id, "circle_apply", "circle", circle.id, circle.name)
    db.commit()
    return {"id": request.id, "circle_id": circle.id, "circle_name": circle.name, "status": "pending"}


@router.get("/join-requests/mine")
def my_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": r.id, "circle_id": c.id, "circle_name": c.name, "status": r.status,
             "review_reason": r.review_reason, "created_at": r.created_at}
            for r, c in db.query(JoinRequest, Circle).join(Circle, Circle.id == JoinRequest.circle_id)
            .filter(JoinRequest.user_id == user.id).order_by(JoinRequest.created_at.desc()).all()]


@router.get("/{circle_id}/join-requests")
def join_requests(circle_id: int, ctx=Depends(require_circle_member), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_circle_manager(db, ctx[0], user.id):
        raise HTTPException(status_code=403, detail="仅圈主和管理员可以审核")
    return [{"id": r.id, "user_id": u.id, "nickname": u.nickname, "username": u.username,
             "message": r.message, "created_at": r.created_at}
            for r, u in db.query(JoinRequest, User).join(User, User.id == JoinRequest.user_id)
            .filter(JoinRequest.circle_id == circle_id, JoinRequest.status == "pending").order_by(JoinRequest.created_at).all()]


@router.patch("/{circle_id}/join-requests/{request_id}")
def review_join(circle_id: int, request_id: int, data: JoinReview, ctx=Depends(require_circle_member),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    circle = ctx[0]
    if not is_circle_manager(db, circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主和管理员可以审核")
    # Serialize approvals with joining and role changes on this circle.
    db.query(Circle).filter_by(id=circle_id).with_for_update().one()
    request = db.query(JoinRequest).filter_by(id=request_id, circle_id=circle_id).with_for_update().first()
    if not request:
        raise HTTPException(status_code=404, detail="申请不存在")
    if request.status != "pending":
        return {"id": request.id, "status": request.status}
    request.status, request.review_reason = data.status, data.reason.strip()
    request.reviewed_by, request.reviewed_at = user.id, datetime.now()
    if data.status == "approved":
        member = db.query(CircleMember).filter_by(circle_id=circle_id, user_id=request.user_id).first()
        if not member:
            member = CircleMember(circle_id=circle_id, user_id=request.user_id)
            db.add(member)
            db.flush()
            record_activity(db, request.user_id, circle_id, "circle_join", "circle", circle_id, circle.name,
                            event_key=f"membership:join:{member.id}")
    notify(db, [request.user_id], "join_result", "入圈申请已通过" if data.status == "approved" else "入圈申请未通过",
           circle.name + (f"：{request.review_reason}" if request.review_reason else ""), circle_id)
    record_activity(db, user.id, circle_id, "join_review", "circle", circle_id, f"申请 #{request.id}")
    db.commit()
    return {"id": request.id, "status": request.status}


@router.get("/{circle_id}", response_model=CircleOut)
def get_circle(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle, _ = ctx
    count = db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count()
    return _circle_out(circle, user.id, count, ctx[1].role)


@router.get("/{circle_id}/members", response_model=list[MemberOut])
def list_members(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    circle, _ = ctx
    rows = (
        db.query(CircleMember, User)
        .join(User, User.id == CircleMember.user_id)
        .filter(CircleMember.circle_id == circle_id)
        .order_by(CircleMember.joined_at)
        .all()
    )
    return [
        MemberOut(
            user_id=u.id,
            username=u.username,
            nickname=u.nickname,
            avatar=avatar_url(u),
            joined_at=m.joined_at,
            is_owner=u.id == circle.owner_id,
            role="owner" if u.id == circle.owner_id else m.role,
        )
        for m, u in rows
    ]


@router.delete("/{circle_id}/members/{user_id}")
def remove_or_leave(
    circle_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle = db.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="圈子不存在")
    is_self = user_id == user.id
    if not is_self and not is_circle_manager(db, circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主和管理员可移出成员")
    if is_self and is_circle_owner(circle, user.id):
        member_count = db.query(CircleMember).filter(CircleMember.circle_id == circle_id).count()
        if member_count > 1:
            raise HTTPException(status_code=400, detail="请先转让圈主再退出")
        # sole owner: dissolve
        files = _circle_files(db, circle_id)
        record_activity(db, user.id, circle_id, "circle_delete", "circle", circle_id, circle.name)
        db.delete(circle)
        db.commit()
        cleanup(*files)
        return {"ok": True, "dissolved": True}

    member = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == circle_id, CircleMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if is_circle_owner(circle, user_id):
        raise HTTPException(status_code=400, detail="不能移出圈主")
    if not is_self and not is_circle_owner(circle, user.id) and member.role == "admin":
        raise HTTPException(status_code=403, detail="管理员不能移出其他管理员")
    if not is_self:
        notify(db, [user_id], "member_removed", "已被移出圈子", circle.name, circle_id)
    record_activity(db, user.id, circle_id, "circle_leave" if is_self else "member_remove",
                    "circle", circle_id, circle.name if is_self else f"成员 #{user_id}")
    db.delete(member)
    db.commit()
    return {"ok": True}


@router.post("/{circle_id}/invite-code/rotate")
def rotate_invite(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle, _ = ctx
    if not is_circle_manager(db, circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主可重置邀请码")
    circle.invite_code = _invite_code()
    record_activity(db, user.id, circle_id, "circle_invite", "circle", circle_id, circle.name)
    db.commit()
    return {"invite_code": circle.invite_code}


@router.patch("/{circle_id}/settings", response_model=CircleOut)
def update_settings(
    circle_id: int,
    data: CircleSettingsIn,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle, _ = ctx
    if not is_circle_owner(circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主可修改圈子设置")
    if data.allow_member_invite is not None:
        circle.allow_member_invite = data.allow_member_invite
    if data.name is not None:
        circle.name = data.name.strip()
    if data.description is not None:
        circle.description = data.description.strip() or None
    if data.cover_color is not None:
        circle.cover_color = data.cover_color
    record_activity(db, user.id, circle_id, "circle_edit", "circle", circle_id, circle.name)
    db.commit()
    count = db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count()
    return _circle_out(circle, user.id, count)


@router.post("/{circle_id}/transfer")
def transfer_owner(
    circle_id: int,
    data: CircleTransferIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle = db.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="圈子不存在")
    if not is_circle_owner(circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主可转让")
    target_member = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == circle_id, CircleMember.user_id == data.user_id)
        .first()
    )
    if not target_member:
        raise HTTPException(status_code=400, detail="目标用户不是圈子成员")
    if data.user_id == user.id:
        raise HTTPException(status_code=400, detail="请选择其他成员")
    circle.owner_id = data.user_id
    target_member.role = "member"
    notify(db, [data.user_id], "owner_transfer", "你已成为圈主", circle.name, circle_id)
    record_activity(db, user.id, circle_id, "circle_transfer", "circle", circle_id, f"新圈主 #{data.user_id}")
    db.commit()
    return {"ok": True, "owner_id": data.user_id}


@router.delete("/{circle_id}")
def dissolve_circle(
    circle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle = db.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="圈子不存在")
    if not is_circle_owner(circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主可解散圈子")
    files = _circle_files(db, circle_id)
    record_activity(db, user.id, circle_id, "circle_delete", "circle", circle_id, circle.name)
    db.delete(circle)
    db.commit()
    cleanup(*files)
    return {"ok": True}


def _circle_files(db, circle_id):
    rows = db.query(Media).join(Post).filter(Post.circle_id == circle_id).all()
    paths = []
    for m in rows:
        paths.append(absolute_from_upload(m.original_path))
        if m.preview_path:
            paths.append(absolute_from_upload(m.preview_path))
    return paths


@router.patch("/{circle_id}/members/{member_id}/role")
def set_member_role(circle_id: int, member_id: int, data: RoleUpdate, ctx=Depends(require_circle_member),
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    circle = db.query(Circle).filter_by(id=circle_id).with_for_update().one()
    if not is_circle_owner(circle, user.id):
        raise HTTPException(status_code=403, detail="仅圈主可以任免管理员")
    if member_id == circle.owner_id:
        raise HTTPException(status_code=400, detail="不能修改圈主角色")
    member = db.query(CircleMember).filter_by(circle_id=circle_id, user_id=member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role != data.role:
        member.role = data.role
        notify(db, [member_id], "role_changed", "圈子角色已更新", f"{circle.name}：{'管理员' if data.role == 'admin' else '普通成员'}", circle_id)
        record_activity(db, user.id, circle_id, "member_role", "circle", circle_id, f"成员 #{member_id}")
    db.commit()
    return {"user_id": member_id, "role": member.role}


@router.get("/{circle_id}/announcements")
def announcements(circle_id: int, ctx=Depends(require_circle_member), db: Session = Depends(get_db)):
    return [{"id": a.id, "title": a.title, "content": a.content, "nickname": u.nickname, "created_at": a.created_at}
            for a, u in db.query(Announcement, User).join(User, User.id == Announcement.user_id)
            .filter(Announcement.circle_id == circle_id).order_by(Announcement.created_at.desc(), Announcement.id.desc()).all()]


@router.post("/{circle_id}/announcements")
def publish_announcement(circle_id: int, data: AnnouncementIn, ctx=Depends(require_circle_member),
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_circle_manager(db, ctx[0], user.id):
        raise HTTPException(status_code=403, detail="仅圈主和管理员可以发布公告")
    if not data.title.strip() or not data.content.strip():
        raise HTTPException(status_code=400, detail="请填写公告标题与内容")
    item = Announcement(circle_id=circle_id, user_id=user.id, title=data.title.strip(), content=data.content.strip())
    db.add(item)
    db.flush()
    members = [uid for (uid,) in db.query(CircleMember.user_id).filter(CircleMember.circle_id == circle_id, CircleMember.user_id != user.id)]
    notify(db, members, "announcement", "新的圈子公告", f"{ctx[0].name}：{item.title}", circle_id)
    record_activity(db, user.id, circle_id, "announcement_create", "circle", item.id, item.title,
                    event_key=f"announcement:create:{item.id}")
    db.commit()
    return {"id": item.id}


@router.delete("/{circle_id}/announcements/{announcement_id}")
def delete_announcement(circle_id: int, announcement_id: int, ctx=Depends(require_circle_member),
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_circle_manager(db, ctx[0], user.id):
        raise HTTPException(status_code=403, detail="仅圈主和管理员可以删除公告")
    item = db.query(Announcement).filter_by(id=announcement_id, circle_id=circle_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="公告不存在")
    record_activity(db, user.id, circle_id, "announcement_delete", "circle", item.id, item.title)
    db.delete(item)
    db.commit()
    return {"ok": True}
