"""玩法接口：回忆盲盒、年度/月度回顾、圈友打卡、猜照片计分。"""
from __future__ import annotations

import random
from collections import Counter
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import (
    Album,
    Challenge,
    ChallengeCheckin,
    CircleMember,
    GuessAttempt,
    Media,
    Post,
    PostLike,
    User,
)
from ..notifications import notify
from ..security import get_current_user, is_circle_manager, require_circle_member
from .posts import post_item

router = APIRouter(tags=["play"])

MONTH_NAMES = [
    "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]


def _post_query(db: Session):
    return db.query(Post).options(
        joinedload(Post.media),
        joinedload(Post.comments),
        joinedload(Post.user),
        joinedload(Post.album),
        joinedload(Post.circle),
    )


# ---------- 回忆盲盒 ----------

@router.get("/api/circles/{circle_id}/memory-box")
def memory_box(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    """优先「往年今日」，其次 45 天前的旧记录，最后全圈随机。"""
    _circle, _member = ctx
    q = _post_query(db).filter(Post.circle_id == circle_id)
    today = date.today()

    candidates = q.filter(
        func.month(Post.event_date) == today.month,
        func.day(Post.event_date) == today.day,
        func.year(Post.event_date) < today.year,
    ).all()
    reason = "往年今日"

    if not candidates:
        candidates = q.filter(Post.event_date <= today - timedelta(days=45)).all()
        reason = "旧时光"

    if not candidates:
        candidates = q.all()
        reason = "随机回忆"

    if not candidates:
        return {"reason": reason, "post": None}

    post = random.choice(candidates)
    return {
        "reason": reason,
        "years_ago": max(0, today.year - post.event_date.year),
        "post": post_item(post).model_dump(mode="json"),
    }


# ---------- 年度 / 月度回顾 ----------

def _longest_streak(days: list[date]) -> int:
    if not days:
        return 0
    ordered = sorted(set(days))
    best = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        best = max(best, run)
    return best


@router.get("/api/circles/{circle_id}/recap")
def recap(
    circle_id: int,
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    _circle, _member = ctx
    posts = _post_query(db).filter(Post.circle_id == circle_id).all()
    if not posts:
        raise HTTPException(status_code=404, detail="圈子里还没有记录")

    if year is None:
        year = max(p.event_date.year for p in posts)
    rows = [
        p for p in posts
        if p.event_date.year == year and (month is None or p.event_date.month == month)
    ]
    if not rows:
        raise HTTPException(status_code=404, detail="这段时间还没有记录")

    photos = videos = audios = 0
    places: set[str] = set()
    people: Counter = Counter()
    tags: Counter = Counter()
    for p in rows:
        for m in p.media:
            if m.kind == "photo":
                photos += 1
            elif m.kind == "video":
                videos += 1
            elif m.kind == "audio":
                audios += 1
        if p.location_name:
            places.add(p.location_name)
        people[p.user_id] += 1
        if p.activity_tag:
            tags[p.activity_tag] += 1

    ids = [p.id for p in rows]
    like_rows = dict(
        db.query(PostLike.post_id, func.count(PostLike.id))
        .filter(PostLike.post_id.in_(ids))
        .group_by(PostLike.post_id)
        .all()
    ) if ids else {}
    hottest = max(rows, key=lambda p: like_rows.get(p.id, 0))

    nicknames = {p.user_id: (p.user.nickname or p.user.username) for p in rows if p.user}
    top_people = [
        {"user_id": uid, "name": nicknames.get(uid, "?"), "count": n}
        for uid, n in people.most_common(3)
    ]
    top_tags = [{"tag": t, "count": n} for t, n in tags.most_common(4)]

    dates = [p.event_date for p in rows]
    ordered = sorted(rows, key=lambda p: (p.event_date, p.created_at))
    cover = next((m.id for m in ordered[0].media if m.kind == "photo"), None)
    if cover is None:
        cover = next((m.id for p in rows for m in p.media if m.kind == "photo"), None)

    return {
        "year": year,
        "month": month,
        "label": f"{year} 年" + (f" {month} 月" if month else ""),
        "posts": len(rows),
        "photos": photos,
        "videos": videos,
        "audios": audios,
        "media": photos + videos + audios,
        "days": len(set(dates)),
        "places": sorted(places),
        "people": top_people,
        "tags": top_tags,
        "longest_streak": _longest_streak(dates),
        "first_date": ordered[0].event_date,
        "last_date": ordered[-1].event_date,
        "hottest": {
            "post_id": hottest.id,
            "content": hottest.content or "这一刻，没有文字。",
            "likes": like_rows.get(hottest.id, 0),
            "cover": f"/api/media/{cover}/file?variant=preview" if cover else None,
        },
        "summary": "、".join(
            part for part in [
                f"{len(rows)} 条记录",
                f"{photos + videos + audios} 个影像",
                f"{len(places)} 个地方" if places else "",
                f"最长连续 {_longest_streak(dates)} 天" if _longest_streak(dates) > 1 else "",
            ] if part
        ),
    }


# ---------- 圈友打卡 / 共同任务 ----------

class ChallengeIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    tag: str = Field(default="", max_length=32)
    target_count: int = Field(default=5, ge=1, le=99)
    start_date: date
    end_date: date


class CheckinIn(BaseModel):
    note: str = Field(default="", max_length=200)
    post_id: Optional[int] = None


def _challenge_out(challenge: Challenge, user_id: int, db: Session) -> dict:
    rows = challenge.checkins or []
    mine = [c for c in rows if c.user_id == user_id]
    participants = {c.user_id for c in rows}
    today = date.today()
    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description or "",
        "tag": challenge.tag or "",
        "target_count": challenge.target_count,
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat(),
        "created_by": challenge.created_by,
        "creator": (challenge.creator.nickname or challenge.creator.username)
        if challenge.creator else "",
        "total": len(rows),
        "participants": len(participants),
        "mine": len(mine),
        "done": len(rows) >= challenge.target_count,
        "mine_done": len(mine) >= challenge.target_count,
        "active": challenge.start_date <= today <= challenge.end_date,
        "recent": [
            {
                "id": c.id,
                "name": (c.user.nickname or c.user.username) if c.user else "",
                "note": c.note or "",
                "post_id": c.post_id,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in sorted(rows, key=lambda x: x.id, reverse=True)[:5]
        ],
    }


@router.get("/api/circles/{circle_id}/challenges")
def list_challenges(
    circle_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _circle, _member = ctx
    rows = (
        db.query(Challenge)
        .options(
            joinedload(Challenge.checkins).joinedload(ChallengeCheckin.user),
            joinedload(Challenge.creator),
        )
        .filter(Challenge.circle_id == circle_id)
        .order_by(Challenge.end_date.desc(), Challenge.id.desc())
        .all()
    )
    return [_challenge_out(c, user.id, db) for c in rows]


@router.post("/api/circles/{circle_id}/challenges", status_code=201)
def create_challenge(
    circle_id: int,
    data: ChallengeIn,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _circle, _member = ctx
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    challenge = Challenge(
        circle_id=circle_id,
        title=data.title.strip(),
        description=data.description.strip() or None,
        tag=data.tag.strip() or None,
        target_count=data.target_count,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by=user.id,
    )
    db.add(challenge)
    db.flush()
    others = [
        m.user_id
        for m in db.query(CircleMember).filter(
            CircleMember.circle_id == circle_id, CircleMember.user_id != user.id
        )
    ]
    notify(
        db, others, "challenge", "圈里发起了新任务",
        f"{user.nickname or user.username}：{challenge.title}", circle_id,
    )
    db.commit()
    db.refresh(challenge)
    return _challenge_out(challenge, user.id, db)


@router.post("/api/circles/{circle_id}/challenges/{challenge_id}/checkins", status_code=201)
def checkin(
    circle_id: int,
    challenge_id: int,
    data: CheckinIn,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _circle, _member = ctx
    challenge = db.get(Challenge, challenge_id)
    if not challenge or challenge.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    today = date.today()
    if not (challenge.start_date <= today <= challenge.end_date):
        raise HTTPException(status_code=400, detail="任务不在进行中")
    if data.post_id is not None:
        post = db.get(Post, data.post_id)
        if not post or post.circle_id != circle_id:
            raise HTTPException(status_code=400, detail="关联记录不存在")
    db.add(
        ChallengeCheckin(
            challenge_id=challenge.id,
            user_id=user.id,
            post_id=data.post_id,
            note=data.note.strip() or None,
        )
    )
    done_before = len(challenge.checkins)
    db.flush()
    db.refresh(challenge)
    if done_before < challenge.target_count <= len(challenge.checkins):
        members = [
            m.user_id
            for m in db.query(CircleMember).filter(CircleMember.circle_id == circle_id)
        ]
        notify(
            db, members, "challenge_done", "共同任务达成",
            f"「{challenge.title}」已完成 {challenge.target_count} 次打卡", circle_id,
        )
    db.commit()
    db.refresh(challenge)
    return _challenge_out(challenge, user.id, db)


@router.delete("/api/circles/{circle_id}/challenges/{challenge_id}")
def delete_challenge(
    circle_id: int,
    challenge_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle, _member = ctx
    challenge = db.get(Challenge, challenge_id)
    if not challenge or challenge.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if challenge.created_by != user.id and not is_circle_manager(db, circle, user.id):
        raise HTTPException(status_code=403, detail="只有发起人或圈主可以删除任务")
    db.delete(challenge)
    db.commit()
    return {"ok": True}


# ---------- 猜照片升级版（限时 / 计分 / 提示卡） ----------

class GuessAnswerIn(BaseModel):
    media_id: int
    guessed_month: int = Field(ge=1, le=12)
    elapsed_ms: int = Field(default=0, ge=0, le=120000)
    used_hint: bool = False


def _album_photos(db: Session, circle_id: int, album_id: int) -> list[tuple[Media, Post]]:
    album = db.get(Album, album_id)
    if not album or album.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="主题分册不存在")
    rows = (
        db.query(Media, Post)
        .join(Post, Post.id == Media.post_id)
        .filter(Post.album_id == album_id, Media.kind == "photo")
        .all()
    )
    return rows


@router.get("/api/circles/{circle_id}/albums/{album_id}/guess/rounds")
def guess_rounds(
    circle_id: int,
    album_id: int,
    limit: int = Query(default=8, ge=1, le=20),
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    rows = _album_photos(db, circle_id, album_id)
    if not rows:
        return []
    random.shuffle(rows)
    rounds = []
    for media, post in rows[:limit]:
        correct = post.event_date.month
        pool = [m for m in range(1, 13) if m != correct]
        options = [correct] + random.sample(pool, 3)
        random.shuffle(options)
        rounds.append(
            {
                "media_id": media.id,
                "preview_url": f"/api/media/{media.id}/file?variant=preview",
                "post_id": post.id,
                "options": options,
            }
        )
    return rounds


@router.get("/api/circles/{circle_id}/albums/{album_id}/guess/hint")
def guess_hint(
    circle_id: int,
    album_id: int,
    media_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
):
    rows = _album_photos(db, circle_id, album_id)
    target = next(((m, p) for m, p in rows if m.id == media_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="照片不在该分册")
    media, post = target
    return {
        "author": (post.user.nickname or post.user.username) if post.user else "",
        "season": (
            "春天" if post.event_date.month <= 5
            else "夏天" if post.event_date.month <= 8
            else "秋天" if post.event_date.month <= 11
            else "冬天"
        ),
        "place": post.location_name or "",
        "tag": post.activity_tag or "",
    }


@router.post("/api/circles/{circle_id}/albums/{album_id}/guess/answer")
def guess_answer(
    circle_id: int,
    album_id: int,
    data: GuessAnswerIn,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _album_photos(db, circle_id, album_id)
    target = next(((m, p) for m, p in rows if m.id == data.media_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="照片不在该分册")
    _media, post = target
    actual = post.event_date.month
    correct = data.guessed_month == actual

    points = 0
    if correct:
        points = 10
        if data.elapsed_ms and data.elapsed_ms <= 8000:
            points += 5
        if data.used_hint:
            points = max(4, points - 4)
    db.add(
        GuessAttempt(
            album_id=album_id,
            media_id=data.media_id,
            user_id=user.id,
            guessed_month=data.guessed_month,
            correct=correct,
            points=points,
            used_hint=data.used_hint,
        )
    )
    db.commit()

    my_score = (
        db.query(func.coalesce(func.sum(GuessAttempt.points), 0))
        .filter(GuessAttempt.album_id == album_id, GuessAttempt.user_id == user.id)
        .scalar()
        or 0
    )
    rows_score = (
        db.query(GuessAttempt.user_id, func.sum(GuessAttempt.points).label("p"))
        .filter(GuessAttempt.album_id == album_id)
        .group_by(GuessAttempt.user_id)
        .order_by(func.sum(GuessAttempt.points).desc())
        .limit(5)
        .all()
    )
    names = {
        u.id: (u.nickname or u.username)
        for u in db.query(User).filter(User.id.in_([r[0] for r in rows_score])).all()
    } if rows_score else {}
    return {
        "correct": correct,
        "actual_month": actual,
        "actual_label": MONTH_NAMES[actual - 1],
        "author": (post.user.nickname or post.user.username) if post.user else "",
        "event_date": post.event_date.isoformat(),
        "points": points,
        "my_score": int(my_score),
        "scoreboard": [
            {"user_id": uid, "name": names.get(uid, "?"), "points": int(p)}
            for uid, p in rows_score
        ],
    }


@router.get("/api/circles/{circle_id}/albums/{album_id}/guess/scoreboard")
def guess_scoreboard(
    circle_id: int,
    album_id: int,
    ctx=Depends(require_circle_member),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _album_photos(db, circle_id, album_id)
    if not rows:
        return {"scoreboard": [], "my_score": 0, "attempts": 0}
    agg = (
        db.query(
            GuessAttempt.user_id,
            func.sum(GuessAttempt.points).label("points"),
            func.count(GuessAttempt.id).label("attempts"),
        )
        .filter(GuessAttempt.album_id == album_id)
        .group_by(GuessAttempt.user_id)
        .order_by(func.sum(GuessAttempt.points).desc())
        .all()
    )
    names = {
        u.id: (u.nickname or u.username)
        for u in db.query(User).filter(User.id.in_([r[0] for r in agg])).all()
    } if agg else {}
    board = [
        {
            "user_id": uid,
            "name": names.get(uid, "?"),
            "points": int(points or 0),
            "attempts": int(attempts or 0),
        }
        for uid, points, attempts in agg
    ]
    mine = next((b for b in board if b["user_id"] == user.id), None)
    return {
        "scoreboard": board,
        "my_score": mine["points"] if mine else 0,
        "attempts": mine["attempts"] if mine else 0,
    }
