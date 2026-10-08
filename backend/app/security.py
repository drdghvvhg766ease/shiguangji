from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Circle, CircleMember, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码编码长度不能超过 72 字节")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > 72:
        return False
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, auth_version: int = 0, scope: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire, "ver": auth_version, "scope": scope}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_auth_cookie(response: Response, token: str, admin: bool = False) -> None:
    response.set_cookie(
        key=settings.admin_cookie_name if admin else settings.cookie_name,
        value=token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/api/admin" if admin else "/",
    )


def clear_auth_cookie(response: Response, admin: bool = False) -> None:
    response.delete_cookie(settings.admin_cookie_name if admin else settings.cookie_name,
                           path="/api/admin" if admin else "/")


def get_token_from_request(request: Request) -> str | None:
    return request.cookies.get(settings.cookie_name)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return _user_from_token(get_token_from_request(request), db, "user")


def _user_from_token(token: str | None, db: Session, scope: str) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
        if payload.get("scope", "user") != scope:
            raise JWTError("Invalid session scope")
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if payload.get("ver", 0) != user.auth_version:
        raise HTTPException(status_code=401, detail="密码已变更，请重新登录")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="账号已停用")
    return user


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    user = _user_from_token(request.cookies.get(settings.admin_cookie_name), db, "admin")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要平台管理员权限")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = get_token_from_request(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
        user = db.get(User, user_id)
        return user if user and user.status == "active" and payload.get("ver", 0) == user.auth_version and payload.get("scope", "user") == "user" else None
    except (JWTError, ValueError):
        return None


def require_circle_member(
    circle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[Circle, CircleMember]:
    circle = db.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="圈子不存在")
    member = (
        db.query(CircleMember)
        .filter(CircleMember.circle_id == circle_id, CircleMember.user_id == user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="你不是该圈子成员")
    return circle, member


def is_circle_owner(circle: Circle, user_id: int) -> bool:
    return circle.owner_id == user_id


def is_circle_manager(db: Session, circle: Circle, user_id: int) -> bool:
    if is_circle_owner(circle, user_id):
        return True
    return db.query(CircleMember).filter_by(circle_id=circle.id, user_id=user_id, role="admin").first() is not None


def verify_origin(request: Request) -> None:
    """Reject cross-site state-changing requests (CSRF-ish)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = set(settings.allowed_origin_list)
    host = request.headers.get("host", "")
    if host:
        allowed.add(f"http://{host}")
        allowed.add(f"https://{host}")
        # 本机任意端口（开发：用户端 5173 / 管理台 5174）
        if host.startswith("127.0.0.1") or host.startswith("localhost"):
            for port in ("5173", "5174", "8000", "8080", "4173"):
                allowed.add(f"http://127.0.0.1:{port}")
                allowed.add(f"http://localhost:{port}")
    if origin.rstrip("/") not in {a.rstrip("/") for a in allowed}:
        raise HTTPException(status_code=403, detail="非法请求来源")
