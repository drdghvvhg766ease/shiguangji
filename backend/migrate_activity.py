"""Create personal activity history and backfill only verifiable creation events."""
from app.activity import record_activity
from app.database import SessionLocal, engine
from app.models import Album, CircleMember, Comment, MemoryLine, Post, Report, UserActivity


def migrate():
    UserActivity.__table__.create(engine, checkfirst=True)
    db = SessionLocal()
    try:
        existing = {key for (key,) in db.query(UserActivity.event_key) if key}
        count = 0

        def add(user_id, circle_id, action, kind, target_id, label, created_at, post_id=None, key=None):
            nonlocal count
            key = key or f"{kind}:create:{target_id}"
            if key in existing:
                return
            record_activity(db, user_id, circle_id, action, kind, target_id, label,
                            post_id=post_id, event_key=key, created_at=created_at)
            existing.add(key)
            count += 1

        for member in db.query(CircleMember).all():
            if db.query(UserActivity).filter_by(user_id=member.user_id, circle_id=member.circle_id, action="circle_create").first():
                continue
            add(member.user_id, member.circle_id, "circle_join", "circle", member.circle_id,
                member.circle.name, member.joined_at, key=f"membership:join:{member.id}")
        for post in db.query(Post).all():
            add(post.user_id, post.circle_id, "post_create", "post", post.id,
                f"记录 #{post.id}", post.created_at, post.id)
        for model, kind in [(Album, "album"), (MemoryLine, "line")]:
            for item in db.query(model).all():
                add(item.created_by, item.circle_id, f"{kind}_create", kind, item.id, item.title, item.created_at)
        for comment in db.query(Comment).all():
            add(comment.user_id, comment.post.circle_id, "comment_create", "comment", comment.id,
                f"记录 #{comment.post_id}", comment.created_at, comment.post_id)
        for report in db.query(Report).all():
            add(report.reporter_id, report.circle_id, "report_create", "report", report.id,
                f"记录 #{report.original_post_id}", report.created_at, report.original_post_id)
        db.commit()
        print(f"Activity migration applied; backfilled {count} verified events")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
