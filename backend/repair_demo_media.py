"""修复 / 重建演示媒体文件。

数据库里有记录、但 uploads 下文件缺失（例如换机器、uploads 未入库）时使用：
优先用 `frontend/user/public/preview-assets` 里的真实照片做裁剪变体，
资源不可用时退回合成图（无边框、无文字，胶片质感）。

用法（在 backend 目录）:
    .\\.venv\\Scripts\\python.exe repair_demo_media.py          # 只补缺失文件
    .\\.venv\\Scripts\\python.exe repair_demo_media.py --force  # 全部重建
"""
from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.database import SessionLocal
from app.media_utils import make_photo_thumbnail, sha256_file
from app.models import Media

ASSET_DIR = Path(__file__).resolve().parent.parent / "frontend" / "user" / "public" / "preview-assets"

# 演示帖内容 → 原型照片，尽量让画面和文字对得上
POST_PLAN = {
    6: "graduates.jpg",  # 学士服
    7: "friends.jpg",  # 晚霞 · 一起看海
    8: "flowers.jpg",  # 银杏
    9: "friends2.jpg",  # 食堂 / 聚餐
    21: ("graduates.jpg", "city.jpg", "flowers.jpg"),  # 毕业合影三连
    22: ("friends.jpg", "city.jpg"),  # 旅行 · 海风
    25: "dinner.jpg",
    195: "friends.jpg",
    196: "city.jpg",
    197: "flowers.jpg",
    198: "friends2.jpg",
    199: "graduates.jpg",
    200: "city.jpg",
    201: "dinner.jpg",
    202: "graduates.jpg",
}

# 照片比例池：让双列瀑布流高低错落，不再一律 4:3 方块
RATIOS = [(4, 3), (3, 2), (1, 1), (4, 5), (3, 4), (5, 4)]

# 真实素材的可裁比例：只取与原始构图接近的，避免把人裁掉半个
ASSET_RATIOS = {
    "graduates.jpg": [(3, 2), (4, 3)],
    "friends.jpg": [(3, 2), (16, 9)],
    "friends2.jpg": [(3, 2), (4, 3)],
    "city.jpg": [(3, 4), (1, 1)],
    "flowers.jpg": [(3, 2), (1, 1)],
    "dinner.jpg": [(3, 2), (4, 3)],
}

PALETTES = [
    ((247, 242, 234), (224, 122, 95), (129, 178, 154)),
    ((252, 244, 232), (244, 162, 97), (212, 163, 115)),
    ((235, 242, 240), (60, 98, 85), (129, 178, 154)),
    ((36, 48, 72), (224, 122, 95), (247, 242, 234)),
    ((250, 243, 226), (217, 171, 89), (173, 71, 55)),
    ((240, 245, 243), (94, 143, 145), (215, 126, 107)),
    ((251, 243, 244), (224, 128, 154), (165, 81, 108)),
    ((31, 42, 46), (127, 179, 160), (217, 129, 95)),
]

MIRROR_IDS = {20, 22, 197, 200, 207, 211, 213}


def ratio_for(media_id: int) -> tuple[int, int]:
    return RATIOS[media_id % len(RATIOS)]


def grade(im: Image.Image, seed: int) -> Image.Image:
    """轻微调色，让同源照片的变体不完全一样。"""
    rnd = random.Random(seed)
    im = ImageEnhance.Color(im).enhance(0.94 + rnd.random() * 0.22)
    im = ImageEnhance.Contrast(im).enhance(0.96 + rnd.random() * 0.12)
    im = ImageEnhance.Brightness(im).enhance(1.0 + (rnd.random() - 0.5) * 0.06)
    tone = rnd.choice([(255, 248, 240), (246, 250, 255), (255, 252, 244)])
    tint = Image.new("RGB", im.size, tone)
    return Image.blend(im, tint, 0.045)


def real_variant(src: Path, dest: Path, media_id: int) -> None:
    with Image.open(src) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
        choices = ASSET_RATIOS.get(src.name) or [(3, 2)]
        rw, rh = choices[media_id % len(choices)]
        target = rw / rh
        # 先按目标比例做中心裁剪，再留一点横向偏移，避免所有图裁得一模一样
        w, h = im.size
        if w / h > target:
            new_w = int(h * target)
            shift = int((media_id * 37) % max(1, w - new_w) * 0.6)
            box = (shift, 0, shift + new_w, h)
        else:
            new_h = int(w / target)
            shift = int((media_id * 53) % max(1, h - new_h) * 0.6)
            box = (0, shift, w, shift + new_h)
        im = im.crop(box)
        if media_id in MIRROR_IDS:
            im = ImageOps.mirror(im)
        if max(im.size) > 1400:
            im.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        im = grade(im, media_id * 13 + 7)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, format="JPEG", quality=90, optimize=True, progressive=True)


def synthetic_photo(dest: Path, media_id: int) -> None:
    """素材缺失时的兜底：无边框、无文字的柔焦色块照片。"""
    rw, rh = ratio_for(media_id)
    w = 1200
    h = max(600, int(w * rh / rw))
    rnd = random.Random(media_id * 31 + 5)
    base, accent, second = PALETTES[media_id % len(PALETTES)]

    small = Image.new("RGB", (2, 96))
    draw = ImageDraw.Draw(small)
    for y in range(96):
        t = y / 95
        draw.line(
            [(0, y), (1, y)],
            fill=tuple(
                int(base[i] + (int(base[i] * 0.78) - base[i]) * t) for i in range(3)
            ),
        )
    im = small.resize((w, h), Image.Resampling.BICUBIC)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i, color in enumerate((accent, second, accent, second)):
        cx = rnd.randint(0, w)
        cy = rnd.randint(0, h)
        r = int(min(w, h) * (0.26 + rnd.random() * 0.34))
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, 78))
    im = Image.alpha_composite(
        im.convert("RGBA"), overlay.filter(ImageFilter.GaussianBlur(min(w, h) * 0.14))
    ).convert("RGB")
    im = im.filter(ImageFilter.GaussianBlur(1.1))

    # 暗角
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(
        [-w * 0.22, -h * 0.22, w * 1.22, h * 1.22],
        fill=255,
        outline=None,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) * 0.18))
    im = Image.composite(im, ImageEnhance.Brightness(im).enhance(0.72), mask)

    # 胶片颗粒
    noise = Image.effect_noise((w, h), 14).convert("L")
    im = Image.blend(im, Image.merge("RGB", (noise, noise, noise)), 0.035)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, format="JPEG", quality=90, optimize=True, progressive=True)


def pick_asset(media: Media, within: int, index: int, pool: list[Path]) -> Path | None:
    if not pool:
        return None
    planned = POST_PLAN.get(media.post_id or 0)
    if planned:
        names = planned if isinstance(planned, (tuple, list)) else (planned,)
        candidate = ASSET_DIR / names[within % len(names)]
        if candidate.is_file():
            return candidate
    stem = Path(media.original_filename or "").stem.lower()
    hints = {
        "graduation": "graduates.jpg",
        "canteen": "friends2.jpg",
        "dinner": "dinner.jpg",
        "ginkgo": "flowers.jpg",
        "evening": "friends.jpg",
        "trip": "city.jpg",
    }
    for key, name in hints.items():
        if key in stem and (ASSET_DIR / name).is_file():
            return ASSET_DIR / name
    return pool[index % len(pool)]


def main() -> None:
    force = "--force" in sys.argv[1:]
    pool = sorted(p for p in ASSET_DIR.glob("*.jpg") if p.is_file()) if ASSET_DIR.is_dir() else []
    db = SessionLocal()
    try:
        rows = db.query(Media).filter(Media.kind == "photo").all()
        if not rows:
            print("没有照片记录，先运行 seed.py / seed_photos.py")
            return
        rebuilt = 0
        seen_post: dict[int, int] = {}
        for index, media in enumerate(rows):
            original = settings.upload_dir / media.original_path
            if original.is_file() and original.stat().st_size > 0 and not force:
                continue
            original.parent.mkdir(parents=True, exist_ok=True)
            within = seen_post.get(media.post_id or 0, 0)
            seen_post[media.post_id or 0] = within + 1
            asset = pick_asset(media, within, index, pool)
            if asset:
                real_variant(asset, original, media.id)
            else:
                synthetic_photo(original, media.id)
            preview_rel = media.preview_path or f"previews/{original.stem}_thumb.jpg"
            preview = settings.upload_dir / preview_rel
            preview.parent.mkdir(parents=True, exist_ok=True)
            make_photo_thumbnail(original, preview, max_side=960)

            media.preview_path = preview_rel
            media.size_bytes = original.stat().st_size
            media.sha256 = sha256_file(original)
            media.mime_type = "image/jpeg"
            rebuilt += 1
            print(f"rebuilt #{media.id} <- {asset.name if asset else 'synthetic'} -> {media.original_path}")
        db.commit()
        print(f"完成：重建 {rebuilt} / {len(rows)} 张照片（素材 {len(pool)} 张）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
