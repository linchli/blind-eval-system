"""
FastAPI 应用入口
"""
import os
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径，使 from app.xxx 导入能正确解析
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.core.config import UPLOAD_DIR, IMAGE_DIR, THUMB_DIR
from app.core.database import engine, Base, SessionLocal
from app.core.security import hash_password
from app.models import User, SceneCategory, SceneSubcategory, Scene, DeviceModel, Image, ImagePair, EvalSession, Evaluation, RankingResult
from app.api import auth, admin, image, eval as eval_router, stats, cleaning, ranking, batch_upload

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# 判断是否为生产模式（前端已构建）
IS_PRODUCTION = DIST_DIR.exists() and any(DIST_DIR.glob("*.html"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表 + 创建默认用户 + 默认场景数据"""
    Base.metadata.create_all(bind=engine)
    _seed_default_users()
    _seed_default_scenes()
    yield


def _seed_default_users():
    db = SessionLocal()
    try:
        defaults = [
            ("admin", "admin@test.com", "admin123", "admin", "管理员"),
            ("eval", "eval@test.com", "123456", "evaluator", "评审员1"),
        ]
        for username, email, pwd, role, display in defaults:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(
                    username=username,
                    email=email,
                    password_hash=hash_password(pwd),
                    role=role,
                    display_name=display,
                ))
        db.commit()
    finally:
        db.close()


def _seed_default_scenes():
    """创建默认大类、子类、场景"""
    db = SessionLocal()
    try:
        categories = [
            ("公园树荫", "32楼花园"), ("车库", "B4车库"), ("天台", "22楼天台"), ("城市道路", "一楼西南角十字路口"),
        ]
        subcategory_names = ["白天", "低照", "夜晚红外", "夜晚白光"]


        cat_ids = []
        for name, location in categories:
            existing = db.query(SceneCategory).filter(
                SceneCategory.name == name,
                SceneCategory.location == location,
            ).first()
            if existing:
                cat_ids.append(existing.id)
                continue
            cat = SceneCategory(name=name, location=location)
            db.add(cat)
            db.flush()
            cat_ids.append(cat.id)

        sub_ids = []
        for name in subcategory_names:
            existing = db.query(SceneSubcategory).filter(
                SceneSubcategory.name == name,
            ).first()
            if existing:
                sub_ids.append(existing.id)
                continue
            sub = SceneSubcategory(name=name)
            db.add(sub)
            db.flush()
            sub_ids.append(sub.id)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


app = FastAPI(
    title="图像盲评系统",
    description="V0.3 — 图像管理模块",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS - 允许所有来源（开发和生产模式均可通过任意 IP 访问）
allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件 - 图片和缩略图
if IMAGE_DIR.exists():
    app.mount("/uploads/images", StaticFiles(directory=str(IMAGE_DIR), html=False), name="images")
if THUMB_DIR.exists():
    app.mount("/uploads/thumbnails", StaticFiles(directory=str(THUMB_DIR), html=False), name="thumbnails")

# API 路由
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(image.router)
app.include_router(eval_router.router)
app.include_router(stats.router)
app.include_router(cleaning.router)
app.include_router(ranking.router)
app.include_router(batch_upload.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}


# 生产模式：提供前端静态文件
if IS_PRODUCTION:
    # 挂载前端静态资源（JS、CSS、图片等）
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 路由：所有非 API 路径都返回 index.html"""
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
