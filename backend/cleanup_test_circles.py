import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal
from app.media_utils import absolute_from_upload, cleanup
from app.models import Circle, Post

db = SessionLocal()
try:
    # 删测试圈
    for c in db.query(Circle).filter(Circle.name.in_(["E2E小队", "PY圈子"])).all():
        db.delete(c)
    # 删冒烟测试短文案
    for p in db.query(Post).filter(Post.content.like("冒烟%")).all():
        files = []
        for m in p.media:
            try:
                files.append(absolute_from_upload(m.original_path))
                if m.preview_path:
                    files.append(absolute_from_upload(m.preview_path))
            except Exception:
                pass
        db.delete(p)
        cleanup(*files)
    db.commit()
    circle = db.query(Circle).filter(Circle.name == "我们仨").first()
    posts = db.query(Post).filter(Post.circle_id == circle.id).order_by(Post.event_date.desc()).all()
    print("我们仨 posts", len(posts))
    for p in posts:
        print(p.id, p.event_date, p.content[:24], "media", len(p.media))
finally:
    db.close()
