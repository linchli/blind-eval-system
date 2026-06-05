"""
应用配置：MySQL 连接、JWT 密钥、文件路径等
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent.parent

# ==================== MySQL ====================
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "blind_eval")

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    f"?charset=utf8mb4"
)

# ==================== JWT ====================
SECRET_KEY = os.getenv("SECRET_KEY", "blind-eval-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 小时

# ==================== 文件存储 ====================
UPLOAD_DIR = BASE_DIR / "uploads"
IMAGE_DIR = UPLOAD_DIR / "images"
THUMB_DIR = UPLOAD_DIR / "thumbnails"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 评测参数 ====================
REPEAT_RATIO = 0.1  # 重复图对比例 10%
DEFAULT_BATCH_SIZE = 40
REST_AFTER_BATCHES = 3

# ==================== 评分映射 ====================
SCORE_MAP = {
    "a_much":   {"label": "A更好",   "score_a": 2.0, "score_b": 0.0},
    "a_slight": {"label": "A稍好",   "score_a": 1.0, "score_b": 0.0},
    "same":     {"label": "一样好",   "score_a": 0.5, "score_b": 0.5},
    "b_slight": {"label": "B稍好",   "score_a": 0.0, "score_b": 1.0},
    "b_much":   {"label": "B更好",   "score_a": 0.0, "score_b": 2.0},
}

# ==================== 缩略图 ====================
THUMB_SIZE = (300, 300)  # 缩略图最大尺寸

# ==================== 批量上传 ====================
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "1000"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "500"))
