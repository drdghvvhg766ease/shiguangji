from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..database import SessionLocal, get_db
from ..models import Circle, ExportJob, Post, User
from ..security import get_current_user, require_circle_member

router = APIRouter(tags=["exports"])

KIND_DIRS = {"photo": "照片", "video": "视频", "audio": "语音"}
EXT_FALLBACK = {"photo": ".jpg", "video": ".mp4", "audio": ".m4a"}
BAD_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


class ExportCreate(BaseModel):
    date_from: date | None = None
    date_to: date | None = None


class ExportOut(BaseModel):
    id: int
    circle_id: int
    status: str
    date_from: date | None = None
    date_to: date | None = None
    file_name: str | None = None
    file_size: int = 0
    post_count: int = 0
    media_count: int = 0
    skipped_count: int = 0
    message: str = ""
    created_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None
    download_url: str | None = None


def _out(job: ExportJob) -> ExportOut:
    return ExportOut(
        id=job.id,
        circle_id=job.circle_id,
        status=job.status,
        date_from=job.scope_from,
        date_to=job.scope_to,
        file_name=job.file_name,
        file_size=job.file_size,
        post_count=job.post_count,
        media_count=job.media_count,
        skipped_count=job.skipped_count,
        message=job.message,
        created_at=job.created_at,
        finished_at=job.finished_at,
        expires_at=job.expires_at,
        download_url=f"/api/exports/{job.id}/download" if job.status == "ready" else None,
    )


def _safe(value: str | None, fallback: str = "未命名", limit: int = 40) -> str:
    text = BAD_CHARS.sub("_", (value or "").strip()).strip(". ")
    return (text or fallback)[:limit]


def _guess_ext(media) -> str:
    suffix = Path(media.original_filename or "").suffix.lower()
    if suffix and len(suffix) <= 6:
        return suffix
    mime = (media.mime_type or "").lower()
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "quicktime" in mime:
        return ".mov"
    if mime.startswith("audio/"):
        for ext in (".m4a", ".mp3", ".wav", ".ogg", ".webm"):
            if ext[1:] in mime:
                return ext
    return EXT_FALLBACK.get(media.kind, ".bin")


def _human_size(size: int) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _cleanup_expired(db: Session) -> None:
    """清理过期的导出包与记录，避免占满磁盘。"""
    now = datetime.now()
    expired = (
        db.query(ExportJob)
        .filter(ExportJob.expires_at.isnot(None), ExportJob.expires_at < now)
        .all()
    )
    for job in expired:
        if job.file_path:
            try:
                (settings.base_dir / job.file_path).unlink(missing_ok=True)
            except OSError:
                pass
        db.delete(job)
    if expired:
        db.commit()


def _build_archive(job_id: int) -> None:
    """后台线程：把圈子里的记录与原始媒体打包成一个 ZIP。"""
    db = SessionLocal()
    try:
        job = db.get(ExportJob, job_id)
        if job is None:
            return
        job.status = "running"
        job.message = "正在整理记录…"
        db.commit()

        circle = db.get(Circle, job.circle_id)
        if circle is None:
            job.status = "failed"
            job.message = "圈子已不存在"
            db.commit()
            return

        query = (
            db.query(Post)
            .options(
                joinedload(Post.circle),
                joinedload(Post.user),
                joinedload(Post.album),
                joinedload(Post.media),
            )
            .filter(Post.circle_id == job.circle_id)
        )
        if job.scope_from is not None:
            query = query.filter(Post.event_date >= job.scope_from)
        if job.scope_to is not None:
            query = query.filter(Post.event_date <= job.scope_to)
        posts = query.order_by(Post.event_date, Post.id).all()

        span_from = job.scope_from.isoformat() if job.scope_from else "最早"
        span_to = job.scope_to.isoformat() if job.scope_to else "至今"
        root = f"时光迹_{_safe(circle.name, '圈子')}_{span_from}_{span_to}"

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = f"{root}_{stamp}.zip"
        target = settings.export_dir / f"export_{job.id}_{stamp}.zip"

        rows: list[list[str]] = []
        records: list[dict] = []
        media_count = 0
        skipped = 0
        written = 0
        seq = 0

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for post in posts:
                seq += 1
                place = _safe(post.location_name or post.activity_tag, "无地点")
                prefix = f"{post.event_date.isoformat()}_{place}_{seq:03d}"
                media_rows: list[dict] = []
                for offset, media in enumerate(post.media, start=1):
                    source = settings.upload_dir / media.original_path
                    if not source.exists():
                        skipped += 1
                        continue
                    if written + media.size_bytes > settings.export_max_bytes:
                        raise ValueError(
                            f"导出内容超过 {_human_size(settings.export_max_bytes)}，"
                            "请缩小日期范围后重试"
                        )
                    folder = KIND_DIRS.get(media.kind, "其他")
                    arcname = f"{root}/{folder}/{prefix}_{offset:02d}{_guess_ext(media)}"
                    archive.write(source, arcname, compress_type=zipfile.ZIP_STORED)
                    written += media.size_bytes
                    media_count += 1
                    media_rows.append(
                        {
                            "file": arcname.split(f"{root}/", 1)[1],
                            "kind": media.kind,
                            "bytes": media.size_bytes,
                            "sha256": media.sha256,
                            "duration": media.duration_seconds,
                        }
                    )

                author = (post.user.nickname or post.user.username) if post.user else ""
                rows.append(
                    [
                        str(post.id),
                        post.event_date.isoformat(),
                        post.circle.name if post.circle else circle.name,
                        author,
                        post.location_name or "",
                        post.activity_tag or "",
                        post.album.title if post.album else "",
                        (post.content or "").replace("\r\n", "\n"),
                        f"{len(post.media)} 个",
                        "；".join(item["file"] for item in media_rows),
                    ]
                )
                records.append(
                    {
                        "id": post.id,
                        "event_date": post.event_date.isoformat(),
                        "author": author,
                        "location": post.location_name,
                        "latitude": post.latitude,
                        "longitude": post.longitude,
                        "activity_tag": post.activity_tag,
                        "album": post.album.title if post.album else None,
                        "content": post.content,
                        "created_at": post.created_at.isoformat() if post.created_at else None,
                        "media": media_rows,
                    }
                )

            # 清单 CSV：utf-8-sig 便于 Excel 直接打开中文
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(
                ["记录ID", "生活日期", "圈子", "作者", "地点", "标签", "分册", "文字", "媒体数", "媒体文件"]
            )
            writer.writerows(rows)
            archive.writestr(
                f"{root}/记录清单.csv",
                buffer.getvalue().encode("utf-8-sig"),
                compress_type=zipfile.ZIP_DEFLATED,
            )

            payload = {
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "circle": {"id": circle.id, "name": circle.name},
                "range": {"from": job.scope_from.isoformat() if job.scope_from else None,
                          "to": job.scope_to.isoformat() if job.scope_to else None},
                "post_count": len(records),
                "media_count": media_count,
                "skipped_media": skipped,
                "posts": records,
            }
            archive.writestr(
                f"{root}/records.json",
                json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )

            readme = f"""时光迹 · 圈子数据导出

圈子：{circle.name}
范围：{span_from} ～ {span_to}
导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
记录数：{len(records)} 条
媒体文件：{media_count} 个（缺失 {skipped} 个）
压缩包大小：约 {_human_size(target.stat().st_size if target.exists() else 0)}

目录说明
  照片/  原始照片文件，按「生活日期_地点_序号」命名
  视频/  原始视频文件
  语音/  语音记录原始音频
  记录清单.csv  可直接用 Excel 打开，含日期、地点、标签、文字与文件名
  records.json  结构化数据，含经纬度、SHA-256 校验值，便于二次处理

说明
  1. 媒体文件为上传时的原始文件，未做压缩或裁切。
  2. 文件名中的序号与记录一一对应，可与清单互相核对。
  3. 本导出包含圈子内所有成员共同创造的记录，请仅用于个人备份，不要随意外传。
  4. 下载链接会在 {settings.export_expire_hours} 小时后失效，请及时保存到本地。
"""
            archive.writestr(
                f"{root}/README.txt",
                readme.encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )

        job.status = "ready"
        job.file_name = file_name
        job.file_path = str(target.relative_to(settings.base_dir)).replace("\\", "/")
        job.file_size = target.stat().st_size
        job.post_count = len(records)
        job.media_count = media_count
        job.skipped_count = skipped
        job.message = ""
        job.finished_at = datetime.now()
        job.expires_at = datetime.now() + timedelta(hours=settings.export_expire_hours)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 后台任务需把失败原因回写给用户
        db.rollback()
        job = db.get(ExportJob, job_id)
        if job is not None:
            job.status = "failed"
            job.message = str(exc)[:240] or "导出失败"
            job.finished_at = datetime.now()
            db.commit()
    finally:
        db.close()


@router.post("/api/circles/{circle_id}/exports", response_model=ExportOut)
def create_export(
    circle_id: int,
    data: ExportCreate,
    background: BackgroundTasks,
    ctx=Depends(require_circle_member),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    circle, _member = ctx
    if data.date_from and data.date_to and data.date_from > data.date_to:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    _cleanup_expired(db)

    running = (
        db.query(ExportJob)
        .filter(
            ExportJob.user_id == user.id,
            ExportJob.circle_id == circle_id,
            ExportJob.status.in_(("pending", "running")),
        )
        .order_by(ExportJob.id.desc())
        .first()
    )
    if running:
        return _out(running)

    job = ExportJob(
        user_id=user.id,
        circle_id=circle_id,
        status="pending",
        scope_from=data.date_from,
        scope_to=data.date_to,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background.add_task(_build_archive, job.id)
    return _out(job)


@router.get("/api/circles/{circle_id}/exports", response_model=list[ExportOut])
def list_exports(
    circle_id: int,
    ctx=Depends(require_circle_member),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _cleanup_expired(db)
    rows = (
        db.query(ExportJob)
        .filter(ExportJob.circle_id == circle_id, ExportJob.user_id == user.id)
        .order_by(ExportJob.id.desc())
        .limit(10)
        .all()
    )
    return [_out(job) for job in rows]


@router.get("/api/exports/{job_id}", response_model=ExportOut)
def get_export(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(ExportJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    return _out(job)


@router.get("/api/exports/{job_id}/download")
def download_export(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(ExportJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    if job.status != "ready" or not job.file_path:
        raise HTTPException(status_code=409, detail="导出包还没准备好")
    if job.expires_at and job.expires_at < datetime.now():
        raise HTTPException(status_code=410, detail="导出包已过期，请重新导出")
    path = settings.base_dir / job.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="导出文件已被清理，请重新导出")
    return FileResponse(
        path,
        media_type="application/zip",
        filename=job.file_name or path.name,
    )
