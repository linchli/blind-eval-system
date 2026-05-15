

"""
数据库初始化脚本：建表 + 种子数据 + 扫描图像目录
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
from app.core.config import IMAGE_DIR, THUMB_DIR, THUMB_SIZE
from app.models import User, Scene, DeviceModel, Image, ImagePair, EvalSession, Evaluation

from itertools import combinations
from PIL import Image as PILImage


# ==================== 默认用户 ====================
DEFAULT_USERS = [
    ("admin", "admin@test.com", "admin123", "admin", "管理员"),
    ("evaluator1", "eval1@test.com", "eval123", "evaluator", "评审员1"),
    ("evaluator2", "eval2@test.com", "eval123", "evaluator", "评审员2"),
    ("guest", "guest@test.com", "guest123", "guest", "访客"),
]


def create_tables():
    """建表"""
    print("=" * 50)
    print("1. 正在连接数据库并建表...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✅ 数据表创建/验证成功！")
    except Exception as e:
        print(f"   ❌ 建表失败: {e}")
        print("   请检查数据库连接配置（backend/app/core/config.py）")
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


def scan_and_seed_scenes(db):
    """扫描图像目录，初始化场景和机型"""
    print("=" * 50)
    print("3. 正在扫描图像目录，初始化场景和机型...")

    if not IMAGE_DIR.exists():
        print(f"   ⚠️  图像目录不存在: {IMAGE_DIR}")
        return

    scene_folders = sorted([d for d in IMAGE_DIR.iterdir() if d.is_dir()])
    if not scene_folders:
        print("   ⚠️  图像目录下没有场景文件夹")
        return

    for scene_folder in scene_folders:
        folder_name = scene_folder.name  # e.g. scene_park_day
        # 解析场景名称：scene_park_day -> 公园-白天
        parts = folder_name.split("_", 1)  # ["scene", "park_day"]
        if len(parts) < 2:
            print(f"   ⚠️  跳过无法解析的目录: {folder_name}")
            continue

        sub_parts = parts[1].rsplit("_", 1)  # ["park", "day"]
        if len(sub_parts) < 2:
            category, subcategory = parts[1], ""
        else:
            category, subcategory = sub_parts

        # 中文名映射
        category_map = {"park": "公园", "pond": "池塘"}
        subcategory_map = {"day": "白天", "dusk": "傍晚"}
        category_cn = category_map.get(category, category)
        subcategory_cn = subcategory_map.get(subcategory, subcategory)
        name = f"{category_cn}-{subcategory_cn}"

        # 创建或更新场景
        scene = db.query(Scene).filter(Scene.folder_name == folder_name).first()
        if not scene:
            scene = Scene(
                category=category_cn,
                subcategory=subcategory_cn,
                name=name,
                folder_name=folder_name,
                sort_order=0,
            )
            db.add(scene)
            db.flush()
            print(f"   ➕ 创建场景: {name} ({folder_name})")
        else:
            print(f"   ⏭️  场景已存在: {name} ({folder_name})")

        # 扫描机型子目录
        model_folders = sorted([d for d in scene_folder.iterdir() if d.is_dir()])
        for model_folder in model_folders:
            model_folder_name = model_folder.name  # e.g. model_632wb4
            model_name = model_folder_name.replace("model_", "机型-")

            # 创建或更新机型
            model = db.query(DeviceModel).filter(DeviceModel.folder_name == model_folder_name).first()
            if not model:
                model = DeviceModel(
                    name=model_name,
                    folder_name=model_folder_name,
                )
                db.add(model)
                db.flush()
                print(f"      ➕ 创建机型: {model_name} ({model_folder_name})")
            else:
                print(f"      ⏭️  机型已存在: {model_name} ({model_folder_name})")

            # 创建图像记录
            existing_img = db.query(Image).filter(
                Image.scene_id == scene.id,
                Image.model_id == model.id,
            ).first()

            if not existing_img:
                # 扫描该目录下的所有图片文件
                image_files = sorted([
                    f for f in model_folder.iterdir()
                    if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp")
                ])

                for img_file in image_files:
                    image_url = f"/uploads/images/{folder_name}/{model_folder_name}/{img_file.name}"

                    # 生成缩略图
                    thumb_path = ""
                    try:
                        thumb_dir = THUMB_DIR / folder_name / model_folder_name
                        thumb_dir.mkdir(parents=True, exist_ok=True)
                        thumb_file = thumb_dir / img_file.name
                        if not thumb_file.exists():
                            pil_img = PILImage.open(img_file)
                            pil_img.thumbnail(THUMB_SIZE, PILImage.Resampling.LANCZOS)
                            pil_img.save(thumb_file, quality=85)
                        thumb_path = f"/uploads/thumbnails/{folder_name}/{model_folder_name}/{img_file.name}"
                    except Exception as e:
                        print(f"      ⚠️  缩略图生成失败: {img_file.name} - {e}")

                    img_record = Image(
                        scene_id=scene.id,
                        model_id=model.id,
                        image_path=image_url,
                        thumb_path=thumb_path,
                    )
                    db.add(img_record)
                    print(f"         ➕ 录入图像: {img_file.name}")
            else:
                print(f"         ⏭️  图像记录已存在: {scene.name} / {model_name}")

    db.flush()


def generate_all_pairs(db):
    """为所有场景生成配对"""
    print("=" * 50)
    print("4. 正在为所有场景生成图像配对...")

    scenes = db.query(Scene).all()
    for scene in scenes:
        images = db.query(Image).filter(Image.scene_id == scene.id).all()
        if len(images) < 2:
            print(f"   ⚠️  场景 {scene.name} 图像不足2张，跳过配对")
            continue

        existing_pairs = db.query(ImagePair).filter(ImagePair.scene_id == scene.id).all()
        existing_set = {(p.image_a_id, p.image_b_id) for p in existing_pairs}

        new_count = 0
        max_sort = max((p.sort_order for p in existing_pairs), default=0)
        for img_a, img_b in combinations(images, 2):
            pair_key = (min(img_a.id, img_b.id), max(img_a.id, img_b.id))
            if pair_key not in existing_set:
                max_sort += 1
                db.add(ImagePair(
                    scene_id=scene.id,
                    image_a_id=pair_key[0],
                    image_b_id=pair_key[1],
                    sort_order=max_sort,
                ))
                new_count += 1

        if new_count > 0:
            print(f"   ➕ 场景 {scene.name}: 生成 {new_count} 对新配对")
        else:
            print(f"   ⏭️  场景 {scene.name}: 无新配对")

    db.flush()


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

    # 3. 扫描图像目录，初始化场景、机型、图像
    db = SessionLocal()
    try:
        scan_and_seed_scenes(db)
        generate_all_pairs(db)
        db.commit()
        print()
        print("✅ 数据库初始化全部完成！")
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

    print()


if __name__ == "__main__":
    init_db()

