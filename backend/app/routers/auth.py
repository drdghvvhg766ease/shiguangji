from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
import io
import uuid
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, UserOut, ProfileUpdate, PasswordUpdate
from ..media_utils import absolute_from_upload, cleanup
from ..security import (
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已被占用")
    user = User(
        username=username,
        nickname=data.nickname.strip() or username,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.auth_version)
    set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    token = create_access_token(user.id, user.auth_version)
    set_auth_cookie(response, token)
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.patch("/profile", response_model=UserOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.nickname.strip():
        raise HTTPException(status_code=400, detail="昵称不能为空")
    user.nickname = data.nickname.strip()
    db.commit()
    return user


@router.post("/password")
def change_password(data: PasswordUpdate, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(data.new_password)
    user.auth_version += 1
    db.commit()
    set_auth_cookie(response, create_access_token(user.id, user.auth_version))
    return {"ok": True}


@router.post("/avatar", response_model=UserOut)
async def update_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if file.content_type not in settings.photo_mime_types:
        raise HTTPException(status_code=400, detail="头像支持 JPEG、PNG、WebP")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像不能超过 5 MB")
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP") or max(image.size) > 12000:
                raise ValueError()
            avatar = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), (256, 256), method=Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="头像文件无效")
    folder = settings.upload_dir / "avatars"
    folder.mkdir(exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.jpg"
    old = absolute_from_upload(user.avatar) if user.avatar else None
    try:
        avatar.save(path, "JPEG", quality=90)
        user.avatar = f"avatars/{path.name}"
        db.commit()
    except Exception:
        db.rollback()
        cleanup(path)
        raise
    if old:
        cleanup(old)
    return user


@router.get("/users/{user_id}/avatar")
def get_avatar(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target or not target.avatar:
        raise HTTPException(status_code=404, detail="头像不存在")
    path = absolute_from_upload(target.avatar)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, no-cache"})
