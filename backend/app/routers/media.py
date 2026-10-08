from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..media_utils import absolute_from_upload
from ..models import CircleMember, Media, Post, User
from ..security import get_current_user

router = APIRouter(prefix="/api/media", tags=["media"])

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def _ensure_media_access(db: Session, media: Media, user: User) -> Post:
    post = db.get(Post, media.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="媒体不存在")
    # 平台管理员为审核可查看媒体
    if user.is_admin:
        return post
    ok = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == post.circle_id, CircleMember.user_id == user.id)
        .first()
    )
    if not ok:
        raise HTTPException(status_code=403, detail="无权访问该媒体")
    return post


def _file_response(path: Path, mime: str, filename: str | None = None, as_attachment: bool = False) -> Response:
    headers = {}
    if as_attachment and filename:
        # RFC 5987 for non-ascii filenames
        from urllib.parse import quote

        headers["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(filename)}"
        )
    return FileResponse(path, media_type=mime, headers=headers)


def _stream_range(path: Path, mime: str, range_header: str | None) -> Response:
    file_size = path.stat().st_size
    if not range_header:
        return FileResponse(path, media_type=mime, headers={"Accept-Ranges": "bytes"})

    m = RANGE_RE.fullmatch(range_header)
    if not m:
        raise HTTPException(status_code=416, detail="Range 无效", headers={"Content-Range": f"bytes */{file_size}"})
    start_s, end_s = m.group(1), m.group(2)
    if start_s == "" and end_s == "":
        raise HTTPException(status_code=416, detail="Range 无效", headers={"Content-Range": f"bytes */{file_size}"})
    if start_s == "":
        # suffix: last N bytes
        length = int(end_s)
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else file_size - 1
    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        raise HTTPException(
            status_code=416,
            detail="Range 超界",
            headers={"Content-Range": f"bytes */{file_size}"},
        )
    chunk_size = end - start + 1

    def iterfile():
        with path.open("rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                data = f.read(min(1024 * 1024, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iterfile(),
        status_code=206,
        media_type=mime,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        },
    )


@router.get("/{media_id}/file")
def get_media_file(
    media_id: int,
    variant: str = "preview",
    request: Request = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="媒体不存在")
    _ensure_media_access(db, media, user)

    if variant == "original":
        rel = media.original_path
        mime = media.mime_type
    elif variant == "preview":
        if not media.preview_path:
            raise HTTPException(status_code=404, detail="预览图不存在")
        rel = media.preview_path
        mime = mimetypes.guess_type(rel)[0] or "image/jpeg"
    else:
        raise HTTPException(status_code=400, detail="variant 仅支持 preview|original")

    path = absolute_from_upload(rel)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件缺失")

    # 预览图可短缓存；原文件用 hash 校验，仍要求登录
    cache = "private, max-age=300" if variant == "preview" else "private, max-age=0, must-revalidate"
    headers = {"Cache-Control": cache, "Accept-Ranges": "bytes"}

    # videos support Range for seeking
    if media.kind == "video" and variant == "original":
        resp = _stream_range(path, mime, request.headers.get("range") if request else None)
        resp.headers["Cache-Control"] = cache
        return resp

    return FileResponse(path, media_type=mime, headers=headers)


@router.get("/{media_id}/download")
def download_media(
    media_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="媒体不存在")
    _ensure_media_access(db, media, user)
    path = absolute_from_upload(media.original_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件缺失")
    return _file_response(
        path,
        media.mime_type,
        filename=media.original_filename,
        as_attachment=True,
    )
