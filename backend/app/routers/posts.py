from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..activity import record_activity
from ..database import get_db
from ..media_utils import (
    MediaError,
    atomic_move,
    cleanup,
    make_photo_thumbnail,
    make_video_cover,
    probe_video_duration,
    relative_to_upload,
    save_upload_stream,
    sha256_file,
    unique_path,
    validate_photo_bytes,
    validate_video_file,
)
from ..models import Album, Circle, CircleMember, Comment, Media, Post, PostLike, Report, User
from ..report_utils import detach_reports, post_snapshot
from ..schemas import (
    MediaOut,
    PostListItem,
    PostOut,
    PostUpdate,
    ReportCreate,
    TimelineDay,
    TimelineMonth,
)
from ..security import get_current_user, is_circle_manager, require_circle_member
from ..profiles import avatar_url
from ..notifications import notify
from .lines import ensure_line, descendants

router = APIRouter(tags=["posts"])


def media_out(m: Media) -> MediaOut:
    return MediaOut(
        id=m.id,
        kind=m.kind,
        original_filename=m.original_filename,
        mime_type=m.mime_type,
        size_bytes=m.size_bytes,
        sha256=m.sha256,
        duration_seconds=m.duration_seconds,
        sort_order=m.sort_order,
        preview_url=f"/api/media/{m.id}/file?variant=preview" if m.preview_path else None,
        original_url=f"/api/media/{m.id}/file?variant=original",
        download_url=f"/api/media/{m.id}/download",
    )


def post_item(p: Post) -> PostListItem:
    return PostListItem(
        id=p.id,
        circle_id=p.circle_id,
        circle_name=p.circle.name if p.circle else "",
        user_id=p.user_id,
        album_id=p.album_id,
        line_id=p.album.line_id if p.album and p.album.line_id else p.line_id,
        latitude=p.latitude, longitude=p.longitude, location_name=p.location_name,
        content=p.content,
        event_date=p.event_date,
        activity_tag=p.activity_tag,
        created_at=p.created_at,
        username=p.user.username if p.user else "",
        nickname=p.user.nickname if p.user else "",
        media=[media_out(m) for m in p.media],
        comment_count=len(p.comments) if p.comments is not None else 0,
    )


def post_detail(p: Post) -> PostOut:
    comments = []
    for c in p.comments or []:
        comments.append(
            {
                "id": c.id,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at,
                "username": c.user.username if c.user else "",
                "nickname": c.user.nickname if c.user else "",
                "avatar": avatar_url(c.user),
                "reply_to_id": c.reply_to_id,
                "reply_to_name": c.reply_to_name,
            }
        )
    return PostOut(
        id=p.id,
        circle_id=p.circle_id,
        circle_name=p.circle.name if p.circle else "",
        user_id=p.user_id,
        album_id=p.album_id,
        line_id=p.album.line_id if p.album and p.album.line_id else p.line_id,
        latitude=p.latitude, longitude=p.longitude, location_name=p.location_name,
        content=p.content,
        event_date=p.event_date,
        activity_tag=p.activity_tag,
        created_at=p.created_at,
        updated_at=p.updated_at,
        username=p.user.username if p.user else "",
        nickname=p.user.nickname if p.user else "",
        media=[media_out(m) for m in p.media],
        comments=comments,
        avatar=avatar_url(p.user),
        comment_count=len(comments),
    )


def _load_post_query(db: Session):
    return db.query(Post).options(
        joinedload(Post.media),
        joinedload(Post.comments).joinedload(Comment.user),
        joinedload(Post.user),
        joinedload(Post.album),
        joinedload(Post.circle),
    )


@router.post("/api/circles/{circle_id}/posts", response_model=PostOut)
async def create_post(
    circle_id: int,
    content: str = Form(default=""),
    event_date: str = Form(...),
    activity_tag: Optional[str] = Form(default=None),
    album_id: Optional[int] = Form(default=None),
    line_id: Optional[int] = Form(default=None),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    location_name: Optional[str] = Form(default=None),
    files: list[UploadFile] = Form(default=[]),
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle, _ = ctx
    ensure_line(db, circle_id, line_id)
    _validate_location(latitude, longitude, location_name)
    try:
        ed = date.fromisoformat(event_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="生活日期格式错误，应为 YYYY-MM-DD")

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张照片或一段视频")

    kinds: set[str] = set()
    for f in files:
        mime = (f.content_type or "").lower()
        if mime in settings.photo_mime_types:
            kinds.add("photo")
        elif mime in settings.video_mime_types:
            kinds.add("video")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {mime or f.filename}")
    if kinds == {"photo", "video"}:
        raise HTTPException(status_code=400, detail="照片与视频暂不能混在同一条记录中")
    if "video" in kinds and len(files) > 1:
        raise HTTPException(status_code=400, detail="每条记录只能上传一段视频")
    if "photo" in kinds and len(files) > settings.max_photos_per_post:
        raise HTTPException(status_code=400, detail=f"每条最多 {settings.max_photos_per_post} 张照片")

    if album_id is not None:
        album = db.get(Album, album_id)
        if not album or album.circle_id != circle_id:
            raise HTTPException(status_code=400, detail="主题分册不存在或不属于该圈子")

    post = Post(
        circle_id=circle_id,
        user_id=user.id,
        album_id=album_id,
        line_id=line_id, latitude=latitude, longitude=longitude,
        location_name=location_name.strip() if location_name else None,
        content=content.strip(),
        event_date=ed,
        activity_tag=(activity_tag or "").strip() or None,
    )
    db.add(post)
    db.flush()

    tmp_paths = []
    saved_paths = []
    try:
        for idx, upload in enumerate(files):
            mime = (upload.content_type or "").lower()
            is_photo = mime in settings.photo_mime_types
            tmp_path = unique_path(
                settings.tmp_dir,
                upload.filename or "upload.bin",
                ".jpg" if is_photo else ".mp4",
            )
            tmp_paths.append(tmp_path)
            size = await save_upload_stream(upload, tmp_path)
            if is_photo:
                if size > settings.max_photo_bytes:
                    raise MediaError("单张照片不能超过 10 MB")
                validate_photo_bytes(tmp_path, mime)
                final = unique_path(settings.photo_dir, upload.filename or "photo.jpg", ".jpg")
                atomic_move(tmp_path, final)
                saved_paths.append(final)
                tmp_paths.remove(tmp_path)
                preview = settings.preview_dir / f"{final.stem}_thumb{final.suffix}"
                saved_paths.append(preview)
                try:
                    make_photo_thumbnail(final, preview)
                except Exception:
                    preview = None
                digest = sha256_file(final)
                db.add(
                    Media(
                        post_id=post.id,
                        kind="photo",
                        original_filename=upload.filename or final.name,
                        mime_type=mime,
                        original_path=relative_to_upload(final),
                        preview_path=relative_to_upload(preview) if preview and preview.exists() else None,
                        size_bytes=size,
                        sha256=digest,
                        duration_seconds=None,
                        sort_order=idx,
                    )
                )
            else:
                if size > settings.max_video_bytes:
                    raise MediaError("视频不能超过 100 MB")
                duration = validate_video_file(tmp_path, mime)
                if duration is not None and duration > settings.max_video_seconds + 0.5:
                    raise MediaError("视频不能超过 3 分钟")
                final = unique_path(settings.video_dir, upload.filename or "video.mp4", ".mp4")
                atomic_move(tmp_path, final)
                saved_paths.append(final)
                tmp_paths.remove(tmp_path)
                cover = settings.preview_dir / f"{final.stem}_cover.jpg"
                saved_paths.append(cover)
                cover_ok = make_video_cover(final, cover)
                digest = sha256_file(final)
                db.add(
                    Media(
                        post_id=post.id,
                        kind="video",
                        original_filename=upload.filename or final.name,
                        mime_type=mime,
                        original_path=relative_to_upload(final),
                        preview_path=relative_to_upload(cover) if cover_ok else None,
                        size_bytes=size,
                        sha256=digest,
                        duration_seconds=duration if duration is not None else probe_video_duration(final),
                        sort_order=0,
                    )
                )
        db.flush()
        record_activity(db, user.id, circle_id, "post_create", "post", post.id,
                        f"记录 #{post.id}", post_id=post.id)
        db.commit()
    except MediaError as e:
        db.rollback()
        cleanup(*tmp_paths, *saved_paths)
        raise HTTPException(status_code=400, detail=e.message)
    except Exception:
        db.rollback()
        cleanup(*tmp_paths, *saved_paths)
        raise

    post = _load_post_query(db).filter(Post.id == post.id).one()
    return _social_detail(db, post, user)


@router.get("/api/circles/{circle_id}/posts", response_model=list[PostListItem])
def list_posts(
    circle_id: int,
    member: Optional[int] = None,
    album_id: Optional[int] = None,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    q = _load_post_query(db).filter(Post.circle_id == circle_id)
    if member:
        q = q.filter(Post.user_id == member)
    if album_id:
        q = q.filter(Post.album_id == album_id)
    rows = q.order_by(Post.event_date.desc(), Post.created_at.desc()).all()
    return [post_item(p) for p in rows]


@router.get("/api/posts/{post_id}", response_model=PostOut)
def get_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = _load_post_query(db).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_member(db, post.circle_id, user.id)
    return _social_detail(db, post, user)


@router.post("/api/posts/{post_id}/reports")
def create_report(post_id: int, data: ReportCreate,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Lock the target record so concurrent duplicate submissions serialize.
    post = db.query(Post).filter(Post.id == post_id).with_for_update().first()
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_member(db, post.circle_id, user.id)
    reason = data.reason.strip()
    if data.report_type == "其他" and not reason:
        raise HTTPException(status_code=400, detail="请填写举报说明")
    existing = db.query(Report).filter(Report.post_id == post_id,
        Report.reporter_id == user.id, Report.status == "pending").first()
    if existing:
        return {"id": existing.id, "status": existing.status}
    report = Report(post_id=post.id, original_post_id=post.id, circle_id=post.circle_id,
        reporter_id=user.id, report_type=data.report_type, reason=reason,
        snapshot=post_snapshot(post))
    db.add(report)
    db.flush()
    record_activity(db, user.id, post.circle_id, "report_create", "report", report.id,
                    f"记录 #{post.id}", post_id=post.id)
    db.commit()
    return {"id": report.id, "status": report.status}


@router.patch("/api/posts/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    data: PostUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的记录")
    _ensure_member(db, post.circle_id, user.id)
    if "line_id" in data.model_fields_set:
        ensure_line(db, post.circle_id, data.line_id)
        post.line_id = data.line_id
    if {"latitude", "longitude", "location_name"} & data.model_fields_set:
        lat = data.latitude if "latitude" in data.model_fields_set else post.latitude
        lng = data.longitude if "longitude" in data.model_fields_set else post.longitude
        name = data.location_name if "location_name" in data.model_fields_set else post.location_name
        _validate_location(lat, lng, name)
        post.latitude, post.longitude, post.location_name = lat, lng, name.strip() if name else None
    if data.content is not None:
        post.content = data.content.strip()
    if data.event_date is not None:
        post.event_date = data.event_date
    if data.activity_tag is not None:
        post.activity_tag = data.activity_tag.strip() or None
    if data.album_id is not None:
        if data.album_id == 0:
            post.album_id = None
        else:
            album = db.get(Album, data.album_id)
            if not album or album.circle_id != post.circle_id:
                raise HTTPException(status_code=400, detail="主题分册不存在或不属于该圈子")
            post.album_id = data.album_id
    record_activity(db, user.id, post.circle_id, "post_edit", "post", post.id,
                    f"记录 #{post.id}", post_id=post.id)
    db.commit()
    post = _load_post_query(db).filter(Post.id == post_id).one()
    return _social_detail(db, post, user)


@router.delete("/api/posts/{post_id}")
def delete_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..media_utils import absolute_from_upload

    post = db.query(Post).options(joinedload(Post.media)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    circle = db.get(Circle, post.circle_id)
    if post.user_id != user.id and not (circle and is_circle_manager(db, circle, user.id)):
        raise HTTPException(status_code=403, detail="无权删除该记录")
    _ensure_member(db, post.circle_id, user.id)
    media_files = []
    for m in post.media:
        try:
            media_files.append(absolute_from_upload(m.original_path))
            if m.preview_path:
                media_files.append(absolute_from_upload(m.preview_path))
        except Exception:
            pass
    detach_reports(db, post)
    record_activity(db, user.id, post.circle_id, "post_delete", "post", post.id,
                    f"记录 #{post.id}", post_id=post.id)
    db.delete(post)
    db.commit()
    cleanup(*media_files)
    return {"ok": True}


@router.get("/api/circles/{circle_id}/timeline", response_model=list[TimelineMonth])
def timeline(
    circle_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    line_id: Optional[int] = None,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    q = _load_post_query(db).filter(Post.circle_id == circle_id)
    if line_id is not None:
        ids = descendants(db, circle_id, line_id)
        q = q.outerjoin(Album, Album.id == Post.album_id).filter(or_(
            Album.line_id.in_(ids),
            (Album.line_id.is_(None)) & Post.line_id.in_(ids)))
    if year:
        q = q.filter(func.year(Post.event_date) == year)
        if month:
            q = q.filter(func.month(Post.event_date) == month)
    return _timeline_months(q)


def _timeline_months(q):
    rows = q.order_by(Post.event_date.desc(), Post.created_at.desc(), Post.id.desc()).all()
    buckets: dict[tuple[int, int], dict[date, list[Post]]] = {}
    for p in rows:
        key = (p.event_date.year, p.event_date.month)
        buckets.setdefault(key, {}).setdefault(p.event_date, []).append(p)

    result: list[TimelineMonth] = []
    for (y, m) in sorted(buckets.keys(), reverse=True):
        days = []
        total = 0
        for d in sorted(buckets[(y, m)].keys(), reverse=True):
            posts = buckets[(y, m)][d]
            total += len(posts)
            days.append(TimelineDay(event_date=d, posts=[post_item(p) for p in posts]))
        result.append(TimelineMonth(year=y, month=m, days=days, post_count=total))
    return result


def _validate_location(latitude, longitude, name):
    import math
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="经纬度必须同时填写")
    if latitude is not None and (not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="经纬度无效")
    if name and len(name) > 128:
        raise HTTPException(status_code=400, detail="地点名称过长")


def _ensure_member(db: Session, circle_id: int, user_id: int) -> None:
    ok = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == circle_id, CircleMember.user_id == user_id)
        .first()
    )
    if not ok:
        raise HTTPException(status_code=403, detail="你不是该圈子成员")


def _social_detail(db, post, user):
    result = post_detail(post)
    result.like_count = db.query(PostLike).filter_by(post_id=post.id).count()
    result.liked = db.query(PostLike).filter_by(post_id=post.id, user_id=user.id).first() is not None
    return result


@router.put("/api/posts/{post_id}/like")
def like_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter_by(id=post_id).with_for_update().first()
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_member(db, post.circle_id, user.id)
    if not db.query(PostLike).filter_by(post_id=post_id, user_id=user.id).first():
        db.add(PostLike(post_id=post_id, user_id=user.id))
        if post.user_id != user.id:
            notify(db, [post.user_id], "like", "有人赞了你的记录", user.nickname, post.circle_id, post.id)
        record_activity(db, user.id, post.circle_id, "post_like", "post", post.id, f"记录 #{post.id}", post_id=post.id)
    db.commit()
    return {"liked": True, "like_count": db.query(PostLike).filter_by(post_id=post_id).count()}


@router.delete("/api/posts/{post_id}/like")
def unlike_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter_by(id=post_id).with_for_update().first()
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_member(db, post.circle_id, user.id)
    item = db.query(PostLike).filter_by(post_id=post_id, user_id=user.id).first()
    if item:
        db.delete(item)
        record_activity(db, user.id, post.circle_id, "post_unlike", "post", post.id, f"记录 #{post.id}", post_id=post.id)
    db.commit()
    return {"liked": False, "like_count": db.query(PostLike).filter_by(post_id=post_id).count()}
