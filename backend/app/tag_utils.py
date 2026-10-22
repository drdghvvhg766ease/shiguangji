"""圈子活动标签（记录分类）的公共逻辑。"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import CircleTag, Post

DEFAULT_TAG = "日常"
MAX_TAG_LENGTH = 20


class TagError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def normalize_tag(name: str | None) -> str:
    value = " ".join((name or "").split())
    if not value:
        raise TagError("标签名称不能为空")
    if len(value) > MAX_TAG_LENGTH:
        raise TagError(f"标签名称最多 {MAX_TAG_LENGTH} 个字符")
    return value


def tag_counts(db: Session, circle_id: int) -> dict[str, int]:
    rows = (
        db.query(Post.activity_tag, func.count(Post.id))
        .filter(Post.circle_id == circle_id, Post.activity_tag.isnot(None), Post.activity_tag != "")
        .group_by(Post.activity_tag)
        .all()
    )
    return {name: count for name, count in rows}


def next_sort_order(db: Session, circle_id: int) -> int:
    current = (
        db.query(func.max(CircleTag.sort_order))
        .filter(CircleTag.circle_id == circle_id)
        .scalar()
    )
    return int(current or 0) + 1


def get_tag(db: Session, circle_id: int, name: str) -> CircleTag | None:
    return (
        db.query(CircleTag)
        .filter(CircleTag.circle_id == circle_id, CircleTag.name == name)
        .first()
    )


def ensure_tag(db: Session, circle_id: int, name: str | None) -> CircleTag | None:
    """记录里出现的标签自动登记进圈子标签表（不提交事务）。"""
    value = " ".join((name or "").split())
    if not value:
        return None
    value = value[:MAX_TAG_LENGTH]
    existing = get_tag(db, circle_id, value)
    if existing:
        return existing
    tag = CircleTag(circle_id=circle_id, name=value, sort_order=next_sort_order(db, circle_id))
    db.add(tag)
    db.flush()
    return tag


def seed_tags(db: Session, circle_id: int) -> None:
    """首次使用时用已有记录补一份标签表，并保证至少有默认标签。"""
    counts = tag_counts(db, circle_id)
    existing_names = {
        name
        for (name,) in db.query(CircleTag.name).filter(CircleTag.circle_id == circle_id).all()
    }
    order = next_sort_order(db, circle_id)
    names = [DEFAULT_TAG] + [n for n in counts if n != DEFAULT_TAG]
    for name in names:
        if name in existing_names:
            continue
        db.add(CircleTag(circle_id=circle_id, name=name, sort_order=order))
        order += 1
    db.flush()


def tag_list(db: Session, circle_id: int) -> list[dict]:
    counts = tag_counts(db, circle_id)
    rows = (
        db.query(CircleTag)
        .filter(CircleTag.circle_id == circle_id)
        .order_by(CircleTag.sort_order, CircleTag.id)
        .all()
    )
    return [
        {"id": row.id, "name": row.name, "post_count": counts.get(row.name, 0)}
        for row in rows
    ]
