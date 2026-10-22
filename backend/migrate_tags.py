"""Create circle_tags table and seed it from existing posts."""
from app.database import SessionLocal, engine
from app.models import Circle, CircleTag
from app.tag_utils import seed_tags


def migrate():
    CircleTag.__table__.create(engine, checkfirst=True)
    db = SessionLocal()
    try:
        total = 0
        for (circle_id,) in db.query(Circle.id).all():
            before = db.query(CircleTag).filter(CircleTag.circle_id == circle_id).count()
            seed_tags(db, circle_id)
            after = db.query(CircleTag).filter(CircleTag.circle_id == circle_id).count()
            total += after - before
        db.commit()
        print(f"ensured table {CircleTag.__tablename__}, seeded {total} tags")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
