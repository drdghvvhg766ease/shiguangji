from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..activity import record_activity
from ..models import Album, Circle, MemoryLine, Post, User
from ..schemas import LineInput
from ..security import get_current_user, require_circle_member, is_circle_manager

router = APIRouter(prefix="/api/circles/{circle_id}/lines", tags=["lines"])


def ensure_line(db, circle_id, line_id):
    if line_id is None:
        return None
    line = db.get(MemoryLine, line_id)
    if not line or line.circle_id != circle_id:
        raise HTTPException(status_code=400, detail="时间线不属于当前圈子")
    return line


def descendants(db, circle_id, line_id):
    ensure_line(db, circle_id, line_id)
    rows = db.query(MemoryLine).filter(MemoryLine.circle_id == circle_id).all()
    ids = {line_id}
    while True:
        children = {r.id for r in rows if r.parent_id in ids}
        if children <= ids:
            return ids
        ids |= children


@router.get("")
def list_lines(circle_id: int, ctx=Depends(require_circle_member), db: Session = Depends(get_db)):
    return [{"id": line.id, "title": line.title, "parent_id": line.parent_id,
             "kind": line.kind, "created_by": line.created_by,
             "album_count": db.query(Album).filter(Album.line_id == line.id).count()}
            for line in db.query(MemoryLine).filter(MemoryLine.circle_id == circle_id).order_by(MemoryLine.created_at).all()]


@router.post("")
def create_line(circle_id: int, data: LineInput, ctx=Depends(require_circle_member),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_line(db, circle_id, data.parent_id)
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="请输入时间线名称")
    line = MemoryLine(circle_id=circle_id, title=data.title.strip(), kind=data.kind,
                      parent_id=data.parent_id, created_by=user.id)
    db.add(line)
    db.flush()
    record_activity(db, user.id, circle_id, "line_create", "line", line.id, line.title)
    db.commit()
    return {"id": line.id}


def editable(db, circle_id, line_id, user):
    line = ensure_line(db, circle_id, line_id)
    circle = db.get(Circle, circle_id)
    if line.created_by != user.id and not is_circle_manager(db, circle, user.id):
        raise HTTPException(status_code=403, detail="仅创建者或圈主可管理时间线")
    return line


@router.patch("/{line_id}")
def update_line(circle_id: int, line_id: int, data: LineInput, ctx=Depends(require_circle_member),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    line = editable(db, circle_id, line_id, user)
    ensure_line(db, circle_id, data.parent_id)
    if data.parent_id in descendants(db, circle_id, line_id):
        raise HTTPException(status_code=400, detail="不能将时间线放入自身分支")
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="请输入时间线名称")
    line.title, line.parent_id, line.kind = data.title.strip(), data.parent_id, data.kind
    record_activity(db, user.id, circle_id, "line_edit", "line", line.id, line.title)
    db.commit()
    return {"ok": True}


@router.delete("/{line_id}")
def delete_line(circle_id: int, line_id: int, ctx=Depends(require_circle_member),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    line = editable(db, circle_id, line_id, user)
    # Removing the organization preserves records, albums and child branches.
    db.query(MemoryLine).filter(MemoryLine.parent_id == line.id).update({MemoryLine.parent_id: line.parent_id})
    db.query(Album).filter(Album.line_id == line.id).update({Album.line_id: None})
    db.query(Post).filter(Post.line_id == line.id).update({Post.line_id: None})
    record_activity(db, user.id, circle_id, "line_delete", "line", line.id, line.title)
    db.delete(line)
    db.commit()
    return {"ok": True}
