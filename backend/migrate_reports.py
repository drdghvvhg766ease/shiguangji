"""Back up reports and migrate retention fields. Safe to run repeatedly."""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from app.database import engine


def migrate():
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("reports")}
    if {"original_post_id", "snapshot"} <= cols and next(c for c in inspector.get_columns("reports") if c["name"] == "post_id")["nullable"]:
        print("Report migration already applied")
        return
    backup = Path(__file__).parent / "backups"
    backup.mkdir(exist_ok=True)
    with engine.connect() as conn:
        rows = [dict(r) for r in conn.execute(text("SELECT * FROM reports")).mappings()]
    target = backup / f"reports-{datetime.now():%Y%m%d-%H%M%S}.json"
    target.write_text(json.dumps(rows, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    with engine.begin() as conn:
        if "original_post_id" not in cols:
            conn.execute(text("ALTER TABLE reports ADD original_post_id INT NULL"))
        if "snapshot" not in cols:
            conn.execute(text("ALTER TABLE reports ADD snapshot JSON NULL"))
        conn.execute(text("""UPDATE reports r LEFT JOIN posts p ON p.id=r.post_id
            LEFT JOIN users u ON u.id=p.user_id LEFT JOIN circles c ON c.id=r.circle_id
            SET r.original_post_id=COALESCE(r.original_post_id,r.post_id),
            r.snapshot=COALESCE(r.snapshot,JSON_OBJECT('content',COALESCE(p.content,''),
            'author',COALESCE(u.nickname,''),'username',COALESCE(u.username,''),
            'circle_name',COALESCE(c.name,''),'event_date',COALESCE(CAST(p.event_date AS CHAR),'')))"""))
        for fk in inspector.get_foreign_keys("reports"):
            if fk["constrained_columns"] == ["post_id"]:
                name = fk["name"].replace("`", "``")
                conn.execute(text(f"ALTER TABLE reports DROP FOREIGN KEY `{name}`"))
        conn.execute(text("ALTER TABLE reports MODIFY post_id INT NULL, MODIFY original_post_id INT NOT NULL"))
        conn.execute(text("UPDATE reports r LEFT JOIN posts p ON p.id=r.post_id SET r.post_id=NULL WHERE p.id IS NULL"))
        conn.execute(text("ALTER TABLE reports ADD CONSTRAINT fk_reports_retained_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL"))
    print(f"Report migration applied; backup: {target}")


if __name__ == "__main__":
    migrate()
