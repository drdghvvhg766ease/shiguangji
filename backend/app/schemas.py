from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(default="", max_length=32)


class LoginIn(BaseModel):
    username: str
    password: str


class ProfileUpdate(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=64)


class UserOut(ORMModel):
    id: int
    username: str
    nickname: str
    avatar: str | None = None
    is_admin: bool = False
    status: str = "active"
    created_at: datetime

    @field_serializer("avatar")
    def serialize_avatar(self, value):
        from .profiles import avatar_url
        return avatar_url(self)


# ---------- Circle ----------
class CircleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    description: str = Field(default="", max_length=200)
    cover_color: str = Field(default="#E07A5F", max_length=16)


class CircleJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)
    message: str = Field(default="", max_length=200)


class RoleUpdate(BaseModel):
    role: Literal["admin", "member"]


class JoinReview(BaseModel):
    status: Literal["approved", "rejected"]
    reason: str = Field(default="", max_length=200)


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=2000)


class FolderIn(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    share_circle_ids: list[int] = Field(default_factory=list, max_length=30)


class FavoriteIn(BaseModel):
    post_id: int


class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    reply_to_id: int | None = None


class CircleSettingsIn(BaseModel):
    allow_member_invite: bool | None = None
    name: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=200)
    cover_color: str | None = Field(default=None, max_length=16)


class CircleTransferIn(BaseModel):
    user_id: int


class MemberOut(BaseModel):
    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    joined_at: datetime
    is_owner: bool = False
    role: str = "member"


class CircleOut(ORMModel):
    id: int
    name: str
    description: str | None = None
    cover_color: str
    invite_code: str
    owner_id: int
    allow_member_invite: bool
    created_at: datetime
    member_count: int = 0
    is_owner: bool = False
    role: str = "member"
    can_manage: bool = False


# ---------- Album ----------
class AlbumCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    prompt: str = Field(default="", max_length=200)
    line_id: int | None = None


class AlbumUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=64)
    prompt: str | None = Field(default=None, max_length=200)
    line_id: int | None = None


class AlbumOut(ORMModel):
    id: int
    circle_id: int
    title: str
    line_id: int | None = None
    prompt: str | None = None
    created_by: int
    created_at: datetime
    post_count: int = 0
    participant_count: int = 0
    cover_thumbs: list[str] = []  # media id list for collage, max 4


class AlbumDetailOut(AlbumOut):
    participants: list[MemberOut] = []


# ---------- Media / Post ----------
class MediaOut(ORMModel):
    id: int
    kind: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    duration_seconds: float | None = None
    sort_order: int
    preview_url: str | None = None
    original_url: str = ""
    download_url: str = ""


class PostCreateMeta(BaseModel):
    content: str = ""
    event_date: date
    activity_tag: str | None = None
    album_id: int | None = None


class PostUpdate(BaseModel):
    content: str | None = None
    event_date: date | None = None
    activity_tag: str | None = None
    album_id: int | None = None
    line_id: int | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str | None = Field(default=None, max_length=128)


class CommentOut(ORMModel):
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    username: str = ""
    nickname: str = ""
    avatar: str | None = None
    reply_to_id: int | None = None
    reply_to_name: str | None = None


class PostOut(ORMModel):
    id: int
    circle_id: int
    circle_name: str = ""
    user_id: int
    album_id: int | None = None
    line_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    content: str
    event_date: date
    activity_tag: str | None = None
    created_at: datetime
    updated_at: datetime
    username: str = ""
    nickname: str = ""
    avatar: str | None = None
    like_count: int = 0
    liked: bool = False
    media: list[MediaOut] = []
    comments: list[CommentOut] = []
    comment_count: int = 0


class PostListItem(BaseModel):
    id: int
    circle_id: int
    circle_name: str = ""
    user_id: int
    album_id: int | None = None
    line_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    content: str
    event_date: date
    activity_tag: str | None = None
    created_at: datetime
    username: str = ""
    nickname: str = ""
    media: list[MediaOut] = []
    comment_count: int = 0


class TimelineDay(BaseModel):
    event_date: date
    posts: list[PostListItem] = []


class TimelineMonth(BaseModel):
    year: int
    month: int
    days: list[TimelineDay] = []
    post_count: int = 0


class ActivityOut(BaseModel):
    id: int
    circle_id: int
    circle_name: str
    action: str
    action_label: str
    target_kind: str
    target_id: int
    target_label: str
    created_at: datetime
    post_id: int | None = None
    can_open_post: bool = False


class ActivityCircle(BaseModel):
    id: int
    name: str


class PersonalTimelineOut(BaseModel):
    items: list[ActivityOut]
    total: int
    circles: list[ActivityCircle]
    years: list[int]


class AlbumMediaItem(BaseModel):
    media: MediaOut
    post_id: int
    user_id: int
    username: str = ""
    nickname: str = ""
    event_date: date
    activity_tag: str | None = None
    content: str = ""
    album_id: int | None = None


class GuessPhotoItem(BaseModel):
    media_id: int
    preview_url: str
    author_id: int
    author_nickname: str
    event_date: date
    content: str
    post_id: int


class ReportCreate(BaseModel):
    report_type: Literal["骚扰辱骂", "隐私侵权", "广告引流", "其他"]
    reason: str = Field(default="", max_length=1000)


class LineInput(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    parent_id: int | None = None
    kind: Literal["life", "travel", "graduation", "other"] = "life"
