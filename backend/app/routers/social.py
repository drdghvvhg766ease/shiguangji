from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..activity import record_activity
from ..database import get_db
from ..models import CircleMember, FavoriteFolder, FavoriteItem, Notification, Post, User
from ..schemas import FolderIn, FavoriteIn
from ..security import get_current_user
from .posts import _ensure_member, _load_post_query, post_item

router = APIRouter(tags=["messages and favorites"])


def membership_ids(db, user_id):
    return {cid for (cid,) in db.query(CircleMember.circle_id).filter_by(user_id=user_id)}


@router.get("/api/me/notifications")
def messages(unread: bool = False, offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(Notification).filter_by(user_id=user.id)
    q = base.filter_by(is_read=False) if unread else base
    rows = q.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit).all()
    circles = membership_ids(db, user.id)
    post_ids = {p for (p,) in db.query(Post.id).filter(Post.circle_id.in_(circles), Post.id.in_([r.post_id for r in rows if r.post_id]))}
    return {"unread_count": base.filter_by(is_read=False).count(), "total": q.count(),
            "items": [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "is_read": n.is_read,
                       "created_at": n.created_at, "circle_id": n.circle_id, "post_id": n.post_id,
                       "can_open_circle": n.circle_id in circles, "can_open_post": n.post_id in post_ids} for n in rows]}


@router.put("/api/me/notifications/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter_by(user_id=user.id, is_read=False).update({Notification.is_read: True})
    db.commit()
    return {"ok": True}


@router.put("/api/me/notifications/{notification_id}/read")
def read_message(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="消息不存在")
    item.is_read = True
    db.commit()
    return {"ok": True}


def owned_folder(db, folder_id, user):
    folder = db.query(FavoriteFolder).filter_by(id=folder_id, user_id=user.id).with_for_update().first()
    if not folder:
        raise HTTPException(status_code=404, detail="收藏夹不存在")
    return folder


def can_view_folder(db, folder, user):
    if folder.user_id == user.id:
        return True
    return bool(set(folder.share_circle_ids or []) & membership_ids(db, user.id) & membership_ids(db, folder.user_id))


def folder_out(db, folder, user):
    owner = db.get(User, folder.user_id)
    return {"id": folder.id, "title": folder.title, "user_id": folder.user_id,
            "nickname": owner.nickname if owner else "", "is_owner": folder.user_id == user.id,
            "share_circle_ids": folder.share_circle_ids if folder.user_id == user.id else [],
            "shared": bool(folder.share_circle_ids), "item_count": db.query(FavoriteItem).filter_by(folder_id=folder.id).count()}


@router.get("/api/me/favorite-folders")
def folders(post_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(FavoriteFolder).order_by(FavoriteFolder.created_at.desc()).all()
    result = []
    for f in rows:
        if not can_view_folder(db, f, user):
            continue
        item = db.query(FavoriteItem).filter_by(folder_id=f.id, post_id=post_id).first() if post_id and f.user_id == user.id else None
        result.append({**folder_out(db, f, user), "contains_post": bool(item), "item_id": item.id if item else None})
    return result


def validate_folder(db, data, user):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="请输入收藏夹名称")
    if set(data.share_circle_ids) - membership_ids(db, user.id):
        raise HTTPException(status_code=403, detail="只能向自己参加的圈子分享")


@router.post("/api/me/favorite-folders")
def create_folder(data: FolderIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    validate_folder(db, data, user)
    folder = FavoriteFolder(user_id=user.id, title=data.title.strip(), share_circle_ids=sorted(set(data.share_circle_ids)))
    db.add(folder)
    db.commit()
    return folder_out(db, folder, user)


@router.patch("/api/me/favorite-folders/{folder_id}")
def edit_folder(folder_id: int, data: FolderIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    validate_folder(db, data, user)
    folder = owned_folder(db, folder_id, user)
    folder.title, folder.share_circle_ids = data.title.strip(), sorted(set(data.share_circle_ids))
    db.commit()
    return folder_out(db, folder, user)


@router.delete("/api/me/favorite-folders/{folder_id}")
def delete_folder(folder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(owned_folder(db, folder_id, user))
    db.commit()
    return {"ok": True}


@router.get("/api/me/favorite-folders/{folder_id}/items")
def favorite_items(folder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    folder = db.get(FavoriteFolder, folder_id)
    if not folder or not can_view_folder(db, folder, user):
        raise HTTPException(status_code=404, detail="收藏夹不存在或不可见")
    items = db.query(FavoriteItem).filter_by(folder_id=folder_id).order_by(FavoriteItem.created_at.desc()).all()
    # Never return media, excerpts or names from records outside the viewer's circles.
    allowed = membership_ids(db, user.id)
    posts = {p.id: p for p in _load_post_query(db).filter(Post.id.in_([i.post_id for i in items]), Post.circle_id.in_(allowed)).all()}
    return {"folder": folder_out(db, folder, user), "items": [
        {"id": i.id, "post_id": i.post_id, "created_at": i.created_at,
         "post": post_item(posts[i.post_id]) if i.post_id in posts else None} for i in items]}


@router.put("/api/me/favorite-folders/{folder_id}/items")
def add_favorite(folder_id: int, data: FavoriteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_folder(db, folder_id, user)
    post = db.get(Post, data.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="记录不存在")
    _ensure_member(db, post.circle_id, user.id)
    item = db.query(FavoriteItem).filter_by(folder_id=folder_id, post_id=post.id).first()
    if not item:
        item = FavoriteItem(folder_id=folder_id, post_id=post.id)
        db.add(item)
        record_activity(db, user.id, post.circle_id, "favorite_add", "post", post.id, f"记录 #{post.id}", post_id=post.id)
    db.commit()
    return {"id": item.id}


@router.delete("/api/me/favorite-folders/{folder_id}/items/{item_id}")
def remove_favorite(folder_id: int, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_folder(db, folder_id, user)
    item = db.query(FavoriteItem).filter_by(id=item_id, folder_id=folder_id).first()
    if not item:
        return {"ok": True}
    post = db.get(Post, item.post_id)
    if post and post.circle_id in membership_ids(db, user.id):
        record_activity(db, user.id, post.circle_id, "favorite_remove", "post", post.id, f"记录 #{post.id}", post_id=post.id)
    db.delete(item)
    db.commit()
    return {"ok": True}
