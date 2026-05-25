"""
FastAPI 应用入口
"""
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
from contextlib import asynccontextmanager

from app.core.config import UPLOAD_DIR, IMAGE_DIR, THUMB_DIR
from app.core.database import engine, Base, SessionLocal
from app.core.security import hash_password
from app.models import User, Scene, DeviceModel, Image, ImagePair, EvalSession, Evaluation
from app.api import auth, admin, image, eval as eval_router

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表 + 创建默认用户"""
    Base.metadata.create_all(bind=engine)
    _seed_default_users()
    yield


def _seed_default_users():
    db = SessionLocal()
    try:
        defaults = [
            ("admin", "admin123", "admin", "管理员"),
            ("evaluator1", "eval123", "evaluator", "评审员1"),
        ]
        for username, pwd, role, display in defaults:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(
                    username=username,
                    password_hash=hash_password(pwd),
                    role=role,
                    display_name=display,
                ))
        db.commit()
    finally:
        db.close()


app = FastAPI(
    title="图像盲评系统",
    description="V0.3 — 图像管理模块",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
if IMAGE_DIR.exists():
    app.mount("/uploads/images", StaticFiles(directory=str(IMAGE_DIR), html=False), name="images")
if THUMB_DIR.exists():
    app.mount("/uploads/thumbnails", StaticFiles(directory=str(THUMB_DIR), html=False), name="thumbnails")

# API 路由
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(image.router)
app.include_router(eval_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
