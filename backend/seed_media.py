"""为演示账号生成合成照片并挂到种子记录上。

用法: python seed_media.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw

from app.config import settings
from app.database import SessionLocal
from app.media_utils import make_photo_thumbnail, relative_to_upload, sha256_file
from app.models import Album, Circle, Media, Post, User


def draw_photo(path: Path, colors: list[tuple], title: str) -> None:
    w, h = 1080, 810
    im = Image.new("RGB", (w, h), colors[0])
    draw = ImageDraw.Draw(im)
    # soft diagonal bands
    for i, c in enumerate(colors[1:], start=1):
        draw.ellipse([w * 0.1 * i - 80, h * 0.15 * i - 60, w * 0.55 * i, h * 0.7 * i], fill=c)
    draw.rectangle([40, h - 120, w - 40, h - 40], fill=(255, 253, 248))
    draw.rectangle([40, 40, w - 40, 100], fill=(255, 253, 248))
    # simple "tape" corners
    draw.polygon([(40, 40), (120, 40), (40, 120)], fill=(224, 122, 95))
    draw.polygon([(w - 40, 40), (w - 120, 40), (w - 40, 120)], fill=(129, 178, 154))
    im.save(path, format="JPEG", quality=90)
    # label bar only — no font dependency issues
    im2 = Image.open(path)
    d2 = ImageDraw.Draw(im2)
    d2.rectangle([40, h - 120, w - 40, h - 40], fill=(255, 253, 248))
    d2.text((60, h - 100), title, fill=(44, 36, 32))
    im2.save(path, format="JPEG", quality=90)


def main() -> None:
    db = SessionLocal()
    try:
        a = db.query(User).filter(User.username == "demo_a").first()
        b = db.query(User).filter(User.username == "demo_b").first()
        if not a or not b:
            print("请先运行 seed.py")
            return
        circle = db.query(Circle).filter(Circle.name == "我们仨").first()
        if not circle:
            print("未找到演示圈子")
            return
        album = db.query(Album).filter(Album.circle_id == circle.id, Album.title == "毕业季").first()
        today = date.today()
        last_week = today - timedelta(days=7)

        specs = [
            {
                "user": a,
                "content": "学士服试穿，笑到停不下来",
                "event_date": last_week,
                "tag": "毕业",
                "album": album,
                "colors": [(247, 242, 234), (224, 122, 95), (244, 162, 97)],
                "title": "Convocation Dress Rehearsal",
                "filename": "graduation-rehearsal.jpg",
            },
            {
                "user": b,
                "content": "今天的晚霞，像极了四年前报到那天",
                "event_date": today,
                "tag": "日常",
                "album": album,
                "colors": [(36, 48, 72), (224, 122, 95), (129, 178, 154)],
                "title": "Evening Glow",
                "filename": "evening-glow.jpg",
            },
            {
                "user": a,
                "content": "宿舍楼下的银杏终于黄了",
                "event_date": today - timedelta(days=2),
                "tag": "日常",
                "album": None,
                "colors": [(212, 163, 115), (129, 178, 154), (255, 253, 248)],
                "title": "Ginkgo Path",
                "filename": "ginkgo-path.jpg",
            },
            {
                "user": b,
                "content": "食堂新出的糖醋排骨，值得一张",
                "event_date": today - timedelta(days=4),
                "tag": "聚餐",
                "album": None,
                "colors": [(200, 80, 60), (244, 162, 97), (255, 230, 200)],
                "title": "Campus Canteen",
                "filename": "canteen.jpg",
            },
        ]

        existing = db.query(Media).count()
        if existing > 5:
            print("已有较多媒体，跳过。")
            return

        for i, spec in enumerate(specs):
            post = Post(
                circle_id=circle.id,
                user_id=spec["user"].id,
                album_id=spec["album"].id if spec["album"] else None,
                content=spec["content"],
                event_date=spec["event_date"],
                activity_tag=spec["tag"],
            )
            db.add(post)
            db.flush()

            final = settings.photo_dir / f"demo_{i:02d}_{spec['filename']}"
            draw_photo(final, spec["colors"], spec["title"])
            preview = settings.preview_dir / f"demo_{i:02d}_thumb.jpg"
            make_photo_thumbnail(final, preview)
            size = final.stat().st_size
            db.add(
                Media(
                    post_id=post.id,
                    kind="photo",
                    original_filename=spec["filename"],
                    mime_type="image/jpeg",
                    original_path=relative_to_upload(final),
                    preview_path=relative_to_upload(preview),
                    size_bytes=size,
                    sha256=sha256_file(final),
                    sort_order=0,
                )
            )
        db.commit()
        print(f"已写入 {len(specs)} 张演示照片。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
