from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..activity import record_activity
from ..models import Album, Circle, CircleMember, Media, Post, User
from ..schemas import (
    AlbumCreate,
    AlbumDetailOut,
    AlbumMediaItem,
    AlbumOut,
    AlbumUpdate,
    GuessPhotoItem,
    MediaOut,
    MemberOut,
)
from ..security import get_current_user, is_circle_manager, require_circle_member
from .posts import media_out
from .lines import ensure_line

router = APIRouter(tags=["album"])


def _album_out(db: Session, album: Album) -> AlbumOut:
    posts = (
        db.query(Post)
        .options(joinedload(Post.media))
        .filter(Post.album_id == album.id)
        .order_by(Post.created_at.desc())
        .all()
    )
    thumbs: list[str] = []
    for p in posts:
        for m in p.media:
            if m.kind == "photo":
                thumbs.append(str(m.id))
            elif m.preview_path:
                thumbs.append(str(m.id))
            if len(thumbs) >= 4:
                break
        if len(thumbs) >= 4:
            break
    authors = {p.user_id for p in posts}
    return AlbumOut(
        id=album.id,
        circle_id=album.circle_id,
        title=album.title,
        line_id=album.line_id,
        prompt=album.prompt,
        created_by=album.created_by,
        created_at=album.created_at,
        post_count=len(posts),
        participant_count=len(authors),
        cover_thumbs=thumbs,
    )


@router.get("/api/circles/{circle_id}/album", response_model=list[AlbumMediaItem])
def shared_album(
    circle_id: int,
    member: Optional[int] = None,
    month: Optional[str] = Query(default=None, description="YYYY-MM"),
    tag: Optional[str] = None,
    album_id: Optional[int] = None,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Media, Post, User)
        .join(Post, Post.id == Media.post_id)
        .join(User, User.id == Post.user_id)
        .filter(Post.circle_id == circle_id)
    )
    if member:
        q = q.filter(Post.user_id == member)
    if tag:
        q = q.filter(Post.activity_tag == tag)
    if album_id:
        q = q.filter(Post.album_id == album_id)
    if month:
        try:
            y, m = month.split("-")
            q = q.filter(func.year(Post.event_date) == int(y), func.month(Post.event_date) == int(m))
        except ValueError:
            raise HTTPException(status_code=400, detail="month 应为 YYYY-MM")
    rows = q.order_by(Post.event_date.desc(), Media.sort_order).all()
    items = []
    for media, post, user in rows:
        mo = media_out(media)
        items.append(
            AlbumMediaItem(
                media=mo,
                post_id=post.id,
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                event_date=post.event_date,
                activity_tag=post.activity_tag,
                content=post.content,
                album_id=post.album_id,
            )
        )
    return items


@router.get("/api/circles/{circle_id}/albums", response_model=list[AlbumOut])
def list_albums(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    albums = (
        db.query(Album)
        .filter(Album.circle_id == circle_id)
        .order_by(Album.created_at.desc())
        .all()
    )
    return [_album_out(db, a) for a in albums]


@router.post("/api/circles/{circle_id}/albums", response_model=AlbumOut)
def create_album(
    circle_id: int,
    data: AlbumCreate,
    ctx=Depends(require_circle_member),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_line(db, circle_id, data.line_id)
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="请输入分册名称")
    album = Album(
        circle_id=circle_id,
        title=data.title.strip(),
        prompt=data.prompt.strip() or None,
        created_by=user.id,
        line_id=data.line_id,
    )
    db.add(album)
    db.flush()
    record_activity(db, user.id, circle_id, "album_create", "album", album.id, album.title)
    db.commit()
    db.refresh(album)
    return _album_out(db, album)


@router.get("/api/circles/{circle_id}/albums/{album_id}", response_model=AlbumDetailOut)
def album_detail(
    circle_id: int,
    album_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    album = db.get(Album, album_id)
    if not album or album.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="分册不存在")
    base = _album_out(db, album)
    posts = (
        db.query(Post, User)
        .join(User, User.id == Post.user_id)
        .filter(Post.album_id == album.id)
        .all()
    )
    seen: dict[int, MemberOut] = {}
    for post, user in posts:
        if user.id not in seen:
            seen[user.id] = MemberOut(
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                avatar=user.avatar,
                joined_at=post.created_at,
                is_owner=user.id == album.created_by,
            )
    return AlbumDetailOut(**base.model_dump(), participants=list(seen.values()))


@router.patch("/api/circles/{circle_id}/albums/{album_id}", response_model=AlbumOut)
def update_album(
    circle_id: int,
    album_id: int,
    data: AlbumUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    album = db.get(Album, album_id)
    if not album or album.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="分册不存在")
    circle = db.get(Circle, circle_id)
    if album.created_by != user.id and not (circle and is_circle_manager(db, circle, user.id)):
        raise HTTPException(status_code=403, detail="仅创建者或圈主可修改")
    from .posts import _ensure_member
    _ensure_member(db, circle_id, user.id)
    if "line_id" in data.model_fields_set:
        ensure_line(db, circle_id, data.line_id)
        album.line_id = data.line_id
    if data.title is not None:
        if not data.title.strip():
            raise HTTPException(status_code=400, detail="请输入分册名称")
        album.title = data.title.strip()
    if data.prompt is not None:
        album.prompt = data.prompt.strip() or None
    record_activity(db, user.id, circle_id, "album_edit", "album", album.id, album.title)
    db.commit()
    return _album_out(db, album)


@router.delete("/api/circles/{circle_id}/albums/{album_id}")
def delete_album(
    circle_id: int,
    album_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    album = db.get(Album, album_id)
    if not album or album.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="分册不存在")
    circle = db.get(Circle, circle_id)
    if album.created_by != user.id and not (circle and is_circle_manager(db, circle, user.id)):
        raise HTTPException(status_code=403, detail="仅创建者或圈主可删除")
    from .posts import _ensure_member
    _ensure_member(db, circle_id, user.id)
    # 解除归属，不删除记录与媒体
    db.query(Post).filter(Post.album_id == album.id).update({Post.album_id: None})
    record_activity(db, user.id, circle_id, "album_delete", "album", album.id, album.title)
    db.delete(album)
    db.commit()
    return {"ok": True}


@router.get("/api/circles/{circle_id}/albums/{album_id}/guess", response_model=list[GuessPhotoItem])
def guess_pool(
    circle_id: int,
    album_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    """只返回分册中的照片；前端负责抽签/揭晓状态。"""
    album = db.get(Album, album_id)
    if not album or album.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="分册不存在")
    rows = (
        db.query(Media, Post, User)
        .join(Post, Post.id == Media.post_id)
        .join(User, User.id == Post.user_id)
        .filter(Post.album_id == album_id, Media.kind == "photo")
        .order_by(Post.event_date.desc(), Media.sort_order)
        .all()
    )
    return [
        GuessPhotoItem(
            media_id=m.id,
            preview_url=f"/api/media/{m.id}/file?variant=preview",
            author_id=u.id,
            author_nickname=u.nickname or u.username,
            event_date=p.event_date,
            content=p.content,
            post_id=p.id,
        )
        for m, p, u in rows
    ]
