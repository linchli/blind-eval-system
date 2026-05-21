
"""
数据库初始化脚本：建表
用法：在项目根目录执行 uv run python backend/init_db.py
"""
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import engine, Base, SessionLocal
from app.core.security import hash_password
from app.models import User, Scene, DeviceModel, Image, ImagePair, EvalSession, Evaluation

# ==================== 默认用户 ====================
DEFAULT_USERS = [
    ("admin", "admin@test.com", "admin123", "admin", "管理员"),
    ("evaluator1", "eval1@test.com", "eval123", "evaluator", "评审员1"),
]

def create_tables():
    """建表"""
    print("=" * 50)
    print("正在连接数据库并建表...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据表创建/验证成功！")
    except Exception as e:
        print(f"❌ 建表失败: {e}")
        print("请检查数据库连接配置（backend/app/core/config.py）")
        return False
    return True

def seed_users():
    """创建默认用户"""
    print("=" * 50)
    print("2. 正在创建默认用户...")
    db = SessionLocal()
    try:
        for username, email, pwd, role, display in DEFAULT_USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(
                    username=username,
                    email=email,
                    password_hash=hash_password(pwd),
                    role=role,
                    display_name=display,
                ))
                print(f"   ➕ 创建用户: {username} ({role})")
            else:
                print(f"   ⏭️  用户已存在: {username}")
        db.commit()
        print("   ✅ 默认用户初始化完成！")
    except Exception as e:
        print(f"   ❌ 创建默认用户失败: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """完整初始化流程"""
    print()
    print("🚀 开始初始化数据库...")
    print()

    # 1. 建表
    if not create_tables():
        return

    # 2. 创建默认用户
    seed_users()

if __name__ == "__main__":
    init_db()
