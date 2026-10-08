from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..activity import ACTION_LABELS
from ..database import get_db
from ..models import CircleMember, Post, User, UserActivity
from ..schemas import PersonalTimelineOut
from ..security import get_current_user

router = APIRouter(tags=["personal activity"])


@router.get("/api/me/timeline", response_model=PersonalTimelineOut)
def personal_timeline(
    circle_id: int | None = None,
    year: int | None = Query(default=None, ge=1900, le=9999),
    kind: Literal["circle", "post", "album", "line", "comment", "report"] | None = None,
    offset: int = Query(default=0, ge=0),
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base = db.query(UserActivity).filter(UserActivity.user_id == user.id)
    q = base
    if circle_id is not None:
        q = q.filter(UserActivity.circle_id == circle_id)
    if year is not None:
        q = q.filter(func.year(UserActivity.created_at) == year)
    if kind is not None:
        q = q.filter(UserActivity.target_kind == kind)
    total = q.count()
    if before_id is not None:
        cursor = base.filter(UserActivity.id == before_id).first()
        if cursor is None:
            raise HTTPException(status_code=400, detail="分页位置无效")
        q = q.filter(or_(UserActivity.created_at < cursor.created_at,
                         (UserActivity.created_at == cursor.created_at) & (UserActivity.id < cursor.id)))
    rows = q.order_by(UserActivity.created_at.desc(), UserActivity.id.desc()).offset(offset).limit(limit).all()
    accessible = {cid for (cid,) in db.query(CircleMember.circle_id).filter(CircleMember.user_id == user.id)}
    post_ids = {r.post_id for r in rows if r.post_id is not None and r.circle_id in accessible}
    available = {pid for (pid,) in db.query(Post.id).filter(Post.id.in_(post_ids), Post.circle_id.in_(accessible))} if post_ids else set()
    circle_rows = base.order_by(UserActivity.created_at.desc(), UserActivity.id.desc()).with_entities(UserActivity.circle_id, UserActivity.circle_name).all()
    circles = {}
    for cid, name in circle_rows:
        circles.setdefault(cid, {"id": cid, "name": name})
    years = [y for (y,) in base.with_entities(func.year(UserActivity.created_at)).distinct().order_by(func.year(UserActivity.created_at).desc())]
    return {
        "items": [{"id": r.id, "circle_id": r.circle_id, "circle_name": r.circle_name,
                   "action": r.action, "action_label": ACTION_LABELS[r.action],
                   "target_kind": r.target_kind, "target_id": r.target_id,
                   "target_label": r.target_label, "created_at": r.created_at,
                   "post_id": r.post_id, "can_open_post": r.post_id in available}
                  for r in rows],
        "total": total, "circles": list(circles.values()), "years": years,
    }
