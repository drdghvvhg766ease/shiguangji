"""把原型里的真实照片灌进演示数据，替换纯色占位图。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.database import SessionLocal
from app.media_utils import make_photo_thumbnail, relative_to_upload, sha256_file
from app.models import Media, Post

ASSETS = Path(__file__).resolve().parent.parent / "frontend" / "user" / "public" / "preview-assets"

# 原型照片顺序，对应现有演示帖
PLAN = [
    # (匹配帖子内容关键字, [(原文件名, 源图), ...])
    ("学士服", [("graduation-cap.jpg", "graduates.jpg")]),
    ("晚霞", [("evening-with-friends.jpg", "friends.jpg")]),
    ("银杏", [("ginkgo-afternoon.jpg", "flowers.jpg")]),
    ("食堂", [("canteen-night.jpg", "dinner.jpg")]),
    ("g0", [("city-evening.jpg", "city.jpg")]),
    ("g1", [("friends-table.jpg", "friends2.jpg")]),
]


def main() -> None:
    db = SessionLocal()
    try:
        posts = (
            db.query(Post)
            .order_by(Post.id)
            .all()
        )
        used = 0
        for post in posts:
            media_rows = list(post.media)
            if not media_rows:
                continue
            # 根据内容或 id 选一组图
            pair = None
            for key, images in PLAN:
                if key in (post.content or "") or key in f"g{post.id % 10}":
                    pair = images
                    break
            if not pair:
                # 默认轮换
                idx = used % len(PLAN)
                pair = PLAN[idx][1]
            used += 1

            # 为该帖重新写媒体文件（最多用 pair 长度）
            for i, m in enumerate(media_rows[: len(pair)]):
                fname, src_name = pair[i]
                src = ASSETS / src_name
                if not src.exists():
                    continue
                # 覆盖原文件
                dest_name = f"photo_{post.id:03d}_{i}_{src_name}"
                dest = settings.photo_dir / dest_name
                shutil.copy2(src, dest)
                preview = settings.preview_dir / f"{dest.stem}_thumb.jpg"
                make_photo_thumbnail(dest, preview, max_side=640)
                m.original_filename = fname
                m.mime_type = "image/jpeg"
                m.original_path = relative_to_upload(dest)
                m.preview_path = relative_to_upload(preview)
                m.size_bytes = dest.stat().st_size
                m.sha256 = sha256_file(dest)
                m.kind = "photo"
                m.duration_seconds = None
            # 帖子文字若太短，换成有温度的文案
            if post.content in ("g0", "g1") or len(post.content or "") < 4:
                post.content = {
                    0: "终于把这一年的照片整理出来了。",
                    1: "说好只是吃顿饭，最后又聊到店里打烊。",
                    2: "说走就走的短途旅行，风很大但很开心。",
                }.get(post.id % 3, "记下这一刻。")
        db.commit()
        print(f"已更新 {used} 条演示记录的照片。")
        for m in db.query(Media).order_by(Media.id).limit(12):
            print(f"  media#{m.id} post={m.post_id} {m.original_filename} size={m.size_bytes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
