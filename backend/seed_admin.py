"""初始化管理员账号 + 演示举报数据。"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, ensure_database, init_db
from app.models import Circle, Post, Report, User
from app.security import hash_password


def main() -> None:
    ensure_database()
    init_db()
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                nickname="平台管理员",
                password_hash=hash_password("admin123"),
                is_admin=True,
                status="active",
            )
            db.add(admin)
            db.commit()
            print("已创建管理员 admin / admin123")
        else:
            admin.is_admin = True
            admin.status = "active"
            db.commit()
            print("管理员已存在")

        if db.query(Report).count() > 0:
            print("已有举报数据，跳过")
            return

        posts = db.query(Post).order_by(Post.id.desc()).limit(6).all()
        if not posts:
            print("没有帖子，无法生成演示举报")
            return

        demo = [
            ("骚扰辱骂", "在圈内发布针对成员的不友善文字"),
            ("隐私侵权", "照片中包含未经同意公开的个人信息"),
            ("广告引流", "反复发送站外购买链接"),
            ("其他", "视频内容与圈子主题无关"),
            ("广告引流", "疑似推广内容"),
            ("其他", "内容与圈子主题无关"),
        ]
        reporter = db.query(User).filter(User.username == "demo_b").first() or admin
        for i, post in enumerate(posts):
            t, reason = demo[i % len(demo)]
            status = "pending"
            if i == 4:
                status = "dismissed"
            elif i == 5:
                status = "removed"
            db.add(
                Report(
                    post_id=post.id,
                    original_post_id=post.id,
                    circle_id=post.circle_id,
                    reporter_id=reporter.id,
                    report_type=t,
                    reason=reason,
                    status=status,
                    handle_reason="未发现违规；演示" if status == "dismissed" else ("广告引流；演示" if status == "removed" else ""),
                    handled_at=datetime.utcnow() if status != "pending" else None,
                )
            )
        db.commit()
        print(f"已写入 {db.query(Report).count()} 条演示举报")
    finally:
        db.close()


if __name__ == "__main__":
    main()
