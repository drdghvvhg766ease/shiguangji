from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps

from .config import settings


class MediaError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _ext_from_name(name: str, fallback: str) -> str:
    suffix = Path(name).suffix.lower()
    return suffix if suffix else fallback


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def save_upload_stream(upload: UploadFile, dest: Path) -> int:
    """Stream upload to dest; return size. Caller handles hashing."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    return size


def make_photo_thumbnail(src: Path, dest: Path, max_side: int = 640) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((max_side, max_side))
        # keep alpha for webp/png
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        save_kwargs = {"quality": 85}
        if dest.suffix.lower() in (".jpg", ".jpeg"):
            im = im.convert("RGB")
        im.save(dest, **save_kwargs)


def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def probe_video_duration(path: Path) -> float | None:
    if not _ffprobe_available():
        return None
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return float(out.decode().strip())
    except Exception:
        return None


def make_video_cover(src: Path, dest: Path) -> bool:
    """Extract one frame as cover. Returns False if ffmpeg missing/failed."""
    if not _ffmpeg_available():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "00:00:01",
                "-i",
                str(src),
                "-vframes",
                "1",
                "-vf",
                "scale=640:-1",
                str(dest),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return dest.exists() and dest.stat().st_size > 0
    except Exception:
        return False


def validate_photo_bytes(path: Path, mime: str) -> None:
    if mime not in settings.photo_mime_types:
        raise MediaError("仅支持 JPEG / PNG / WebP 照片")
    try:
        with Image.open(path) as im:
            im.verify()
    except Exception:
        raise MediaError("照片文件损坏或不是有效图片")


def validate_video_file(path: Path, mime: str) -> float | None:
    if mime not in settings.video_mime_types:
        raise MediaError("仅支持 MP4 与 MOV 视频")
    duration = probe_video_duration(path)
    if duration is not None and duration > settings.max_video_seconds + 0.5:
        raise MediaError(f"视频时长不能超过 {settings.max_video_seconds // 60} 分钟")
    return duration


def unique_path(directory: Path, original_name: str, fallback_ext: str) -> Path:
    ext = _ext_from_name(original_name, fallback_ext)
    return directory / f"{uuid.uuid4().hex}{ext}"


def relative_to_upload(path: Path) -> str:
    return str(path.relative_to(settings.upload_dir)).replace("\\", "/")


def absolute_from_upload(rel: str) -> Path:
    p = (settings.upload_dir / rel).resolve()
    if not str(p).startswith(str(settings.upload_dir.resolve())):
        raise MediaError("非法路径")
    return p


def cleanup(*paths: Path | None) -> None:
    for p in paths:
        if p and p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def atomic_move(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)
