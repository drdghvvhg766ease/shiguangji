from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..activity import record_activity
from ..notifications import notify
from ..profiles import avatar_url
from ..models import Circle, Comment, Post, User
from ..schemas import CommentOut, CommentIn
from ..security import get_current_user, is_circle_manager, require_circle_member

router = APIRouter(tags=["comments"])


def _comment_out(c: Comment) -> CommentOut:
    return CommentOut(
        id=c.id,
        post_id=c.post_id,
        user_id=c.user_id,
        content=c.content,
        created_at=c.created_at,
        username=c.user.username if c.user else "",
        nickname=c.user.nickname if c.user else "",
        avatar=avatar_url(c.user), reply_to_id=c.reply_to_id, reply_to_name=c.reply_to_name,
    )


@router.get("/api/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    member = True  # checked via require path
    from ..models import CircleMember

    ok = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == post.circle_id, CircleMember.user_id == user.id)
        .first()
    )
    if not ok:
        raise HTTPException(status_code=403, detail="你不是该圈子成员")
    rows = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at)
        .all()
    )
    return [_comment_out(c) for c in rows]


@router.post("/api/posts/{post_id}/comments", response_model=CommentOut)
def add_comment(
    post_id: int,
    payload: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 500:
        raise HTTPException(status_code=400, detail="评论过长")
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    from ..models import CircleMember

    ok = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == post.circle_id, CircleMember.user_id == user.id)
        .first()
    )
    if not ok:
        raise HTTPException(status_code=403, detail="你不是该圈子成员")
    reply = None
    if payload.reply_to_id:
        reply = db.query(Comment).options(joinedload(Comment.user)).filter_by(id=payload.reply_to_id, post_id=post_id).first()
        if not reply:
            raise HTTPException(status_code=400, detail="回复的评论不存在")
    c = Comment(post_id=post_id, user_id=user.id, content=content,
                reply_to_id=reply.id if reply else None,
                reply_to_name=(reply.user.nickname or reply.user.username) if reply else None)
    db.add(c)
    db.flush()
    record_activity(db, user.id, post.circle_id, "comment_create", "comment", c.id,
                    f"记录 #{post.id}", post_id=post.id)
    recipients = {post.user_id}
    if reply:
        recipients.add(reply.user_id)
    notify(db, recipients - {user.id}, "comment", "新的评论回复" if reply else "有人评论了你的记录",
           user.nickname, post.circle_id, post.id)
    db.commit()
    db.refresh(c)
    c = db.query(Comment).options(joinedload(Comment.user)).filter(Comment.id == c.id).one()
    return _comment_out(c)


@router.delete("/api/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="评论不存在")
    post = db.get(Post, c.post_id)
    circle = db.get(Circle, post.circle_id) if post else None
    from .posts import _ensure_member
    _ensure_member(db, post.circle_id, user.id)
    if c.user_id != user.id and not (circle and is_circle_manager(db, circle, user.id)):
        raise HTTPException(status_code=403, detail="无权删除该评论")
    record_activity(db, user.id, post.circle_id, "comment_delete", "comment", c.id,
                    f"记录 #{post.id}", post_id=post.id)
    db.delete(c)
    db.commit()
    return {"ok": True}
