"""圈子活动标签：改名 / 新增 / 删除（会同步到圈内记录）。

圈子成员都可以维护，改动即时同步到该圈所有记录，方便小圈子共同整理分类。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CircleTag, Post
from ..schemas import TagInput, TagOut
from ..security import require_circle_member
from ..tag_utils import (
    DEFAULT_TAG,
    TagError,
    get_tag,
    next_sort_order,
    normalize_tag,
    seed_tags,
    tag_list,
)

router = APIRouter(tags=["tags"])


def _normalized(name: str) -> str:
    try:
        return normalize_tag(name)
    except TagError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.get("/api/circles/{circle_id}/tags", response_model=list[TagOut])
def list_tags(
    circle_id: int,
    _member=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    seed_tags(db, circle_id)
    db.commit()
    return tag_list(db, circle_id)


@router.post("/api/circles/{circle_id}/tags", response_model=list[TagOut])
def create_tag(
    circle_id: int,
    data: TagInput,
    _member=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    name = _normalized(data.name)
    if get_tag(db, circle_id, name):
        raise HTTPException(status_code=409, detail="这个标签已经存在")
    db.add(CircleTag(circle_id=circle_id, name=name, sort_order=next_sort_order(db, circle_id)))
    db.commit()
    return tag_list(db, circle_id)


@router.patch("/api/circles/{circle_id}/tags/{tag_id}", response_model=list[TagOut])
def rename_tag(
    circle_id: int,
    tag_id: int,
    data: TagInput,
    _member=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    tag = db.get(CircleTag, tag_id)
    if not tag or tag.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="标签不存在")
    name = _normalized(data.name)
    if name == tag.name:
        return tag_list(db, circle_id)
    if get_tag(db, circle_id, name):
        raise HTTPException(status_code=409, detail="这个标签已经存在")
    old = tag.name
    (
        db.query(Post)
        .filter(Post.circle_id == circle_id, Post.activity_tag == old)
        .update({Post.activity_tag: name}, synchronize_session=False)
    )
    tag.name = name
    db.commit()
    return tag_list(db, circle_id)


@router.delete("/api/circles/{circle_id}/tags/{tag_id}", response_model=list[TagOut])
def delete_tag(
    circle_id: int,
    tag_id: int,
    fallback: str | None = Query(default=None),
    _member=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    tag = db.get(CircleTag, tag_id)
    if not tag or tag.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="标签不存在")
    rest = [
        row for row in db.query(CircleTag).filter(CircleTag.circle_id == circle_id).all()
        if row.id != tag.id
    ]
    if not rest:
        raise HTTPException(status_code=400, detail="至少保留一个标签")
    names = [row.name for row in rest]
    target = (fallback or "").strip()
    if target not in names:
        target = DEFAULT_TAG if DEFAULT_TAG in names else names[0]
    (
        db.query(Post)
        .filter(Post.circle_id == circle_id, Post.activity_tag == tag.name)
        .update({Post.activity_tag: target}, synchronize_session=False)
    )
    db.delete(tag)
    db.commit()
    return tag_list(db, circle_id)
