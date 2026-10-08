from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import ensure_database, init_db
from .routers import activity, admin, album, auth, circles, comments, lines, media, posts, social
from .security import verify_origin


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_database()
    init_db()
    yield


app = FastAPI(
    title="时光迹 API",
    description="朋友照片 / 生活记录平台 · 毕业设计 V7",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    try:
        verify_origin(request)
    except Exception as e:
        return JSONResponse(status_code=403, content={"detail": getattr(e, "detail", "非法请求来源")})
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "shiguangji"}


app.include_router(auth.router)
app.include_router(circles.router)
app.include_router(posts.router)
app.include_router(activity.router)
app.include_router(social.router)
app.include_router(lines.router)
app.include_router(album.router)
app.include_router(media.router)
app.include_router(comments.router)
app.include_router(admin.router)


# 生产：若存在 frontend/user/dist，可由 FastAPI 直接托管（亦可用 Nginx）
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "user" / "dist"
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "接口不存在"})
        index = _dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "前端未构建"})
