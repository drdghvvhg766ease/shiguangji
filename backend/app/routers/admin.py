"""平台管理后台 API：总览 / 举报审核 / 用户 / 圈子 / 审计。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..media_utils import absolute_from_upload, cleanup
from ..models import AuditLog, Circle, CircleMember, Comment, JoinRequest, Media, Post, Report, User
from ..notifications import notify
from ..security import clear_auth_cookie, create_access_token, get_current_admin, set_auth_cookie, verify_password
from ..schemas import LoginIn, UserOut
from ..report_utils import detach_reports
from .posts import media_out
from .media import get_media_file, download_media

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/auth/login", response_model=UserOut)
def login_admin(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="账号已停用")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="该账号不是平台管理员")
    set_auth_cookie(response, create_access_token(user.id, user.auth_version, "admin"), admin=True)
    return user


@router.get("/auth/me", response_model=UserOut)
def admin_me(admin: User = Depends(get_current_admin)):
    return admin


@router.post("/auth/logout")
def logout_admin(response: Response):
    clear_auth_cookie(response, admin=True)
    return {"ok": True}


@router.get("/media/{media_id}/file")
def admin_media_file(media_id: int, request: Request, variant: str = "preview",
                     admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return get_media_file(media_id=media_id, variant=variant, request=request, user=admin, db=db)


@router.get("/media/{media_id}/download")
def admin_media_download(media_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return download_media(media_id=media_id, user=admin, db=db)


def admin_media_out(media: Media):
    result = media_out(media).model_dump()
    for field in ("preview_url", "original_url", "download_url"):
        if result[field]:
            result[field] = result[field].replace("/api/media/", "/api/admin/media/", 1)
    return result


def _audit(db: Session, admin: User, action: str, target: str, reason: str = "") -> None:
    db.add(AuditLog(admin_id=admin.id, action=action, target=target, reason=reason or ""))


@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    pending = db.query(Report).filter(Report.status == "pending").count()
    removed = db.query(Report).filter(Report.status == "removed").count()
    users = db.query(User).count()
    suspended = db.query(User).filter(User.status == "suspended").count()
    circles = db.query(Circle).count()
    return {
        "pending_reports": pending,
        "removed_reports": removed,
        "users": users,
        "suspended_users": suspended,
        "circles": circles,
        "pending_join_requests": db.query(JoinRequest).filter_by(status="pending").count(),
    }


@router.get("/reports")
def list_reports(
    status: str | None = Query(default="pending"),
    type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = (
        db.query(Report)
        .options(
            joinedload(Report.post).joinedload(Post.user),
            joinedload(Report.post).joinedload(Post.media),
            joinedload(Report.post).joinedload(Post.circle),
            joinedload(Report.reporter),
        )
        .order_by(Report.created_at.desc())
    )
    if status and status != "all":
        query = query.filter(Report.status == status)
    if type and type != "all":
        query = query.filter(Report.report_type == type)
    if q:
        like = f"%{q.strip()}%"
        query = query.outerjoin(Post, Post.id == Report.post_id).outerjoin(User, User.id == Post.user_id).filter(
            or_(
                Post.content.like(like),
                User.username.like(like),
                User.nickname.like(like),
                Report.report_type.like(like),
                Report.reason.like(like),
            )
        )
    rows = query.all()
    items = []
    for r in rows:
        post = r.post
        snapshot = r.snapshot or {}
        media = (post.media[0] if post and post.media else None)
        items.append(
            {
                "id": r.id,
                "post_id": r.original_post_id,
                "circle_id": r.circle_id,
                "circle_name": post.circle.name if post and post.circle else snapshot.get("circle_name", ""),
                "author": post.user.nickname if post and post.user else snapshot.get("author", ""),
                "username": post.user.username if post and post.user else snapshot.get("username", ""),
                "type": r.report_type,
                "reason": r.reason,
                "content": post.content if post else snapshot.get("content", ""),
                "media": [admin_media_out(m) for m in post.media] if post else [],
                "post_deleted": post is None,
                "media_url": f"/api/admin/media/{media.id}/file?variant=preview" if media and media.preview_path else "",
                "media_kind": media.kind if media else "",
                "reporter": r.reporter.nickname if r.reporter else "",
                "created": r.created_at.strftime("%m-%d %H:%M") if r.created_at else "",
                "event_date": post.event_date.isoformat() if post else snapshot.get("event_date", ""),
                "status": r.status,
                "handle_reason": r.handle_reason or "",
            }
        )
    return items


def _get_report(db: Session, report_id: int) -> Report:
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="举报不存在")
    return r


@router.post("/reports/{report_id}/dismiss")
def dismiss_report(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = _get_report(db, report_id)
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="举报已处理")
    reason = (payload.get("reason") or "未发现违规").strip()
    note = (payload.get("note") or "").strip()
    r.status = "dismissed"
    r.handle_reason = f"{reason}；{note}" if note else reason
    r.handled_at = datetime.utcnow()
    _audit(db, admin, "驳回举报", f"举报 #{r.id}", r.handle_reason)
    notify(db, [r.reporter_id], "report_result", "举报处理结果", r.handle_reason, r.circle_id)
    db.commit()
    return {"ok": True, "status": r.status}


@router.post("/reports/{report_id}/remove")
def remove_reported_post(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = _get_report(db, report_id)
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="举报已处理")
    reason = (payload.get("reason") or "其他").strip()
    note = (payload.get("note") or "").strip()
    explanation = f"{reason}；{note}" if note else reason

    post = db.query(Post).options(joinedload(Post.media)).filter(Post.id == r.post_id).first()
    target_id = r.original_post_id
    files = []
    if post:
        for m in post.media:
            try:
                files.append(absolute_from_upload(m.original_path))
                if m.preview_path:
                    files.append(absolute_from_upload(m.preview_path))
            except Exception:
                pass
        detach_reports(db, post, explanation)
        db.delete(post)
    r.status = "removed"
    r.handle_reason = explanation
    r.handled_at = datetime.utcnow()
    _audit(db, admin, "删除记录", f"记录 #{target_id}", explanation)
    notify(db, [r.reporter_id], "report_result", "举报已处理：记录已删除", explanation, r.circle_id)
    db.commit()
    cleanup(*files)
    return {"ok": True, "status": r.status}


@router.get("/users")
def list_users(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.username.like(like), User.nickname.like(like)))
    users = query.all()
    report_counts = dict(
        db.query(Report.post_id, func.count(Report.id)).group_by(Report.post_id).all()
    )
    items = []
    for u in users:
        post_count = db.query(Post).filter(Post.user_id == u.id).count()
        # 被举报 = 其帖子被举报次数
        reported = (
            db.query(Report)
            .join(Post, Post.id == Report.post_id)
            .filter(Post.user_id == u.id)
            .count()
        )
        circle_ids = [
            m.circle_id
            for m in db.query(CircleMember).filter(CircleMember.user_id == u.id).all()
        ]
        circle_names = []
        if circle_ids:
            for c in db.query(Circle).filter(Circle.id.in_(circle_ids)).all():
                circle_names.append(c.name)
        items.append(
            {
                "id": u.id,
                "username": u.username,
                "nickname": u.nickname or u.username,
                "status": u.status,
                "is_admin": u.is_admin,
                "post_count": post_count,
                "reported_count": reported,
                "joined_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
                "circle_ids": circle_ids,
                "circles": circle_names,
            }
        )
    return items


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="不能停用自己")
    if u.is_admin:
        raise HTTPException(status_code=400, detail="不能停用管理员")
    reason = (payload.get("reason") or "其他").strip()
    note = (payload.get("note") or "").strip()
    explanation = f"{reason}；{note}" if note else reason
    u.status = "suspended"
    _audit(db, admin, "停用账号", f"用户 @{u.username}", explanation)
    db.commit()
    return {"ok": True, "status": u.status}


@router.post("/users/{user_id}/restore")
def restore_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    reason = (payload.get("reason") or "复核通过").strip()
    note = (payload.get("note") or "").strip()
    explanation = f"{reason}；{note}" if note else reason
    u.status = "active"
    _audit(db, admin, "恢复账号", f"用户 @{u.username}", explanation)
    db.commit()
    return {"ok": True, "status": u.status}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """永久删除账号：连同其记录、媒体文件、评论。"""
    payload = payload or {}
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if u.is_admin:
        raise HTTPException(status_code=400, detail="不能删除管理员账号")

    reason = (payload.get("reason") or "其他").strip()
    note = (payload.get("note") or "").strip()
    explanation = f"{reason}；{note}" if note else reason

    files: list = []
    if u.avatar:
        files.append(absolute_from_upload(u.avatar))
    if db.query(Circle).filter_by(owner_id=u.id).first():
        raise HTTPException(status_code=400, detail="请先转让或解散该用户拥有的圈子")
    # Preserve shared albums/branches by transferring their authorship to the circle owner.
    from ..models import Album, MemoryLine
    for model in (Album, MemoryLine):
        for item in db.query(model).filter_by(created_by=u.id).all():
            item.created_by = db.get(Circle, item.circle_id).owner_id
    posts = db.query(Post).options(joinedload(Post.media)).filter(Post.user_id == u.id).all()
    for p in posts:
        for m in p.media:
            try:
                files.append(absolute_from_upload(m.original_path))
                if m.preview_path:
                    files.append(absolute_from_upload(m.preview_path))
            except Exception:
                pass
        detach_reports(db, p, explanation)
        db.delete(p)

    # 评论
    db.query(Comment).filter(Comment.user_id == u.id).delete(synchronize_session=False)
    # 成员关系
    db.query(CircleMember).filter(CircleMember.user_id == u.id).delete(synchronize_session=False)
    # 举报
    db.query(Report).filter(Report.reporter_id == u.id).delete(synchronize_session=False)
    # 审计里管理员字段置空
    db.query(AuditLog).filter(AuditLog.admin_id == u.id).update({AuditLog.admin_id: None})
    # 分册创建者若为该用户，保留分册（已删记录会解除归属）

    _audit(db, admin, "删除账号", f"用户 @{u.username}", explanation)
    db.delete(u)
    db.commit()
    cleanup(*files)
    return {"ok": True, "deleted_posts": len(posts)}


@router.get("/circles")
def list_circles(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    circles = db.query(Circle).order_by(Circle.created_at.desc()).all()
    items = []
    for c in circles:
        owner = db.get(User, c.owner_id)
        members = db.query(CircleMember).filter(CircleMember.circle_id == c.id).count()
        posts = db.query(Post).filter(Post.circle_id == c.id).count()
        pending = (
            db.query(Report)
            .filter(Report.circle_id == c.id, Report.status == "pending")
            .count()
        )
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description or "",
                "owner": owner.nickname if owner else "",
                "owner_username": owner.username if owner else "",
                "members": members,
                "posts": posts,
                "pending_reports": pending,
                "admins": db.query(CircleMember).filter_by(circle_id=c.id, role="admin").count(),
                "pending_join_requests": db.query(JoinRequest).filter_by(circle_id=c.id, status="pending").count(),
            }
        )
    return items


@router.get("/audit")
def list_audit(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    items = []
    for a in rows:
        adm = db.get(User, a.admin_id) if a.admin_id else None
        items.append(
            {
                "id": a.id,
                "time": a.created_at.strftime("%m-%d %H:%M") if a.created_at else "",
                "action": a.action,
                "target": a.target,
                "reason": a.reason or "",
                "admin": adm.username if adm else "系统",
            }
        )
    return items
