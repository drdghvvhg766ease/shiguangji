"""演示数据：A/B 账号 + 「我们仨」圈子 + 「毕业季」分册 + 合成照片。

用法:
  cd backend
  python seed.py
  python seed_media.py   # 可选：补演示照片（seed 已内置）
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, ensure_database, init_db
from app.models import Album, Circle, CircleMember, Comment, Media, Post, User
from app.security import hash_password


def main() -> None:
    ensure_database()
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username.in_(["demo_a", "demo_b"])).count() >= 2:
            print("演示账号已存在，跳过。")
            return

        a = User(username="demo_a", nickname="阿晓", password_hash=hash_password("demo1234"))
        b = User(username="demo_b", nickname="小舟", password_hash=hash_password("demo1234"))
        db.add_all([a, b])
        db.flush()

        circle = Circle(
            name="我们仨",
            description="毕业前的最后一个春天",
            cover_color="#E07A5F",
            invite_code="DEMO2026",
            owner_id=a.id,
            allow_member_invite=True,
        )
        db.add(circle)
        db.flush()
        db.add_all(
            [
                CircleMember(circle_id=circle.id, user_id=a.id),
                CircleMember(circle_id=circle.id, user_id=b.id),
            ]
        )

        album = Album(
            circle_id=circle.id,
            title="毕业季",
            prompt="选一张最像毕业季的照片",
            created_by=a.id,
        )
        db.add(album)
        db.flush()

        today = date.today()
        last_week = today - timedelta(days=7)

        # 带演示照片的记录（直接生成合成图，界面一打开就有内容）
        from PIL import Image, ImageDraw

        from app.config import settings
        from app.media_utils import make_photo_thumbnail, relative_to_upload, sha256_file

        def _draw(path: Path, colors: list[tuple], title: str) -> None:
            w, h = 1080, 810
            im = Image.new("RGB", (w, h), colors[0])
            d = ImageDraw.Draw(im)
            for i, c in enumerate(colors[1:], start=1):
                d.ellipse([w * 0.1 * i - 80, h * 0.15 * i - 60, w * 0.55 * i, h * 0.7 * i], fill=c)
            d.polygon([(40, 40), (120, 40), (40, 120)], fill=(224, 122, 95))
            d.polygon([(w - 40, 40), (w - 120, 40), (w - 40, 120)], fill=(129, 178, 154))
            d.rectangle([40, h - 100, w - 40, h - 40], fill=(255, 253, 248))
            d.text((60, h - 85), title, fill=(44, 36, 32))
            im.save(path, format="JPEG", quality=90)

        specs = [
            (a, album, "学士服试穿，笑到停不下来", last_week, "毕业",
             [(247, 242, 234), (224, 122, 95), (244, 162, 97)], "graduation.jpg"),
            (b, album, "今天的晚霞，像极了四年前报到那天", today, "日常",
             [(36, 48, 72), (224, 122, 95), (129, 178, 154)], "sunset.jpg"),
            (a, None, "宿舍楼下的银杏终于黄了", today - timedelta(days=2), "日常",
             [(212, 163, 115), (129, 178, 154), (255, 253, 248)], "ginkgo.jpg"),
            (b, None, "食堂新出的糖醋排骨，值得一张", today - timedelta(days=4), "聚餐",
             [(200, 80, 60), (244, 162, 97), (255, 230, 200)], "canteen.jpg"),
        ]
        first_post = None
        for i, (user, alb, content, ed, tag, colors, fname) in enumerate(specs):
            post = Post(
                circle_id=circle.id,
                user_id=user.id,
                album_id=alb.id if alb else None,
                content=content,
                event_date=ed,
                activity_tag=tag,
            )
            db.add(post)
            db.flush()
            if first_post is None:
                first_post = post
            final = settings.photo_dir / f"seed_{i:02d}_{fname}"
            _draw(final, colors, fname)
            preview = settings.preview_dir / f"seed_{i:02d}_thumb.jpg"
            make_photo_thumbnail(final, preview)
            db.add(
                Media(
                    post_id=post.id,
                    kind="photo",
                    original_filename=fname,
                    mime_type="image/jpeg",
                    original_path=relative_to_upload(final),
                    preview_path=relative_to_upload(preview),
                    size_bytes=final.stat().st_size,
                    sha256=sha256_file(final),
                    sort_order=0,
                )
            )

        db.add(
            Comment(
                post_id=first_post.id,
                user_id=b.id,
                content="这张必须冲印出来贴在宿舍！",
            )
        )
        db.commit()
        print("演示数据写入完成。")
        print("  账号 A: demo_a / demo1234（圈主）")
        print("  账号 B: demo_b / demo1234（成员）")
        print("  邀请码: DEMO2026")
        print("  圈子: 我们仨 · 分册: 毕业季 · 演示照片 4 张")
    finally:
        db.close()


if __name__ == "__main__":
    main()
