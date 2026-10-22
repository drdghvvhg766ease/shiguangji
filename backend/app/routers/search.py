from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Album, CircleMember, Media, Post, User
from ..security import get_current_user

router = APIRouter(tags=["search"])

MAX_LIMIT = 50
SNIPPET_RADIUS = 42


class SearchPost(BaseModel):
    id: int
    circle_id: int
    circle_name: str
    user_id: int
    author_name: str
    event_date: date
    location_name: str | None = None
    content: str = ""
    activity_tag: str | None = None
    snippet: str = ""
    preview_url: str | None = None
    media_id: int | None = None
    kinds: list[str] = []
    media_count: int = 0
    album_title: str | None = None


class SearchAlbum(BaseModel):
    id: int
    circle_id: int
    circle_name: str
    title: str
    prompt: str | None = None
    post_count: int = 0


class SearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    offset: int
    posts: list[SearchPost]
    albums: list[SearchAlbum]
    tags: list[str]
    locations: list[str]


def _escape(value: str) -> str:
    """LIKE 通配符转义，避免用户输入的 % 与 _ 被当成模式。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _member_circle_ids(db: Session, user_id: int) -> list[int]:
    rows = db.query(CircleMember.circle_id).filter(CircleMember.user_id == user_id).all()
    return [row[0] for row in rows]


def _snippet(text: str, keyword: str) -> str:
    """截取命中位置附近的一小段文字，供结果列表显示。"""
    body = (text or "").strip().replace("\n", " ")
    if not body:
        return ""
    if not keyword:
        return body[: SNIPPET_RADIUS * 2] + ("…" if len(body) > SNIPPET_RADIUS * 2 else "")
    at = body.lower().find(keyword.lower())
    if at < 0:
        return body[: SNIPPET_RADIUS * 2] + ("…" if len(body) > SNIPPET_RADIUS * 2 else "")
    start = max(0, at - SNIPPET_RADIUS)
    end = min(len(body), at + len(keyword) + SNIPPET_RADIUS)
    return ("…" if start > 0 else "") + body[start:end] + ("…" if end < len(body) else "")


def _media_summary(post: Post) -> tuple[list[str], int, str | None, int | None]:
    """返回记录包含的媒体类型、数量、预览地址与首条媒体 id。"""
    kinds: list[str] = []
    preview: str | None = None
    first_id: int | None = None
    for item in post.media:
        if item.kind and item.kind not in kinds:
            kinds.append(item.kind)
        if first_id is None:
            first_id = item.id
        if preview is None:
            if item.preview_path:
                preview = f"/api/media/{item.id}/file?variant=preview"
            elif item.kind == "photo":
                preview = f"/api/media/{item.id}/file?variant=original"
    return kinds, len(post.media), preview, first_id


@router.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query("", max_length=64),
    circle_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    member_id: int | None = None,
    kind: str | None = Query(None, pattern="^(photo|video|audio|text)$"),
    album_only: bool = False,
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keyword = q.strip()
    circle_ids = _member_circle_ids(db, user.id)
    if circle_id is not None:
        if circle_id not in circle_ids:
            return SearchResponse(
                query=keyword, total=0, limit=limit, offset=offset,
                posts=[], albums=[], tags=[], locations=[],
            )
        circle_ids = [circle_id]
    if not circle_ids:
        return SearchResponse(
            query=keyword, total=0, limit=limit, offset=offset,
            posts=[], albums=[], tags=[], locations=[],
        )

    query = db.query(Post).options(
        joinedload(Post.circle),
        joinedload(Post.user),
        joinedload(Post.album),
        joinedload(Post.media),
    ).filter(Post.circle_id.in_(circle_ids))

    if keyword:
        pattern = f"%{_escape(keyword)}%"
        query = query.filter(
            or_(
                Post.content.like(pattern, escape="\\"),
                Post.location_name.like(pattern, escape="\\"),
                Post.activity_tag.like(pattern, escape="\\"),
            )
        )
    if date_from is not None:
        query = query.filter(Post.event_date >= date_from)
    if date_to is not None:
        query = query.filter(Post.event_date <= date_to)
    if member_id is not None:
        query = query.filter(Post.user_id == member_id)
    if kind == "text":
        query = query.filter(~Post.media.any())
    elif kind in ("photo", "video", "audio"):
        query = query.filter(Post.media.any(Media.kind == kind))

    total = query.count() if not album_only else 0
    posts: list[SearchPost] = []
    if not album_only:
        # 当前圈排前面，圈内再按生活日期倒序
        current_first = (
            func.field(Post.circle_id, *circle_ids) if len(circle_ids) > 1 else Post.circle_id
        )
        rows = (
            query.order_by(current_first, Post.event_date.desc(), Post.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        for post in rows:
            kinds, count, preview, first_media = _media_summary(post)
            posts.append(
                SearchPost(
                    id=post.id,
                    circle_id=post.circle_id,
                    circle_name=post.circle.name if post.circle else "",
                    user_id=post.user_id,
                    author_name=(post.user.nickname or post.user.username) if post.user else "",
                    event_date=post.event_date,
                    location_name=post.location_name,
                    content=post.content or "",
                    activity_tag=post.activity_tag,
                    snippet=_snippet(post.content, keyword),
                    preview_url=preview,
                    media_id=first_media,
                    kinds=kinds,
                    media_count=count,
                    album_title=post.album.title if post.album else None,
                )
            )

    albums: list[SearchAlbum] = []
    if keyword:
        album_rows = (
            db.query(Album)
            .options(joinedload(Album.circle))
            .filter(Album.circle_id.in_(circle_ids))
            .filter(
                or_(
                    Album.title.like(f"%{_escape(keyword)}%", escape="\\"),
                    Album.prompt.like(f"%{_escape(keyword)}%", escape="\\"),
                )
            )
            .order_by(Album.created_at.desc())
            .limit(6)
            .all()
        )
        counts = dict(
            db.query(Post.album_id, func.count(Post.id))
            .filter(Post.album_id.in_([a.id for a in album_rows] or [0]))
            .group_by(Post.album_id)
            .all()
        )
        for album in album_rows:
            albums.append(
                SearchAlbum(
                    id=album.id,
                    circle_id=album.circle_id,
                    circle_name=album.circle.name if album.circle else "",
                    title=album.title,
                    prompt=album.prompt,
                    post_count=counts.get(album.id, 0),
                )
            )

    # 结果里出现的标签与地点，可在筛选面板里再点选
    scope = db.query(Post).filter(Post.circle_id.in_(circle_ids))
    if keyword:
        pattern = f"%{_escape(keyword)}%"
        scope = scope.filter(
            or_(
                Post.content.like(pattern, escape="\\"),
                Post.location_name.like(pattern, escape="\\"),
                Post.activity_tag.like(pattern, escape="\\"),
            )
        )
    tag_rows = (
        scope.with_entities(Post.activity_tag, func.count(Post.id))
        .filter(Post.activity_tag.isnot(None), Post.activity_tag != "")
        .group_by(Post.activity_tag)
        .order_by(func.count(Post.id).desc())
        .limit(8)
        .all()
    )
    place_rows = (
        scope.with_entities(Post.location_name, func.count(Post.id))
        .filter(Post.location_name.isnot(None), Post.location_name != "")
        .group_by(Post.location_name)
        .order_by(func.count(Post.id).desc())
        .limit(8)
        .all()
    )

    return SearchResponse(
        query=keyword,
        total=total,
        limit=limit,
        offset=offset,
        posts=posts,
        albums=albums,
        tags=[row[0] for row in tag_rows],
        locations=[row[0] for row in place_rows],
    )
