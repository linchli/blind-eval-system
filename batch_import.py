"""
批量导入脚本：从 test 目录导入机型、场景、图像数据
目录结构：
  test/
  ├── models/          # 机型配置JSON
  └── images/          # 场景目录
      └── scene_xxx/   # 各场景下的图像+元信息JSON

用法：python batch_import.py
"""
import sys
import json
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.core.config import IMAGE_DIR, THUMB_DIR, THUMB_SIZE
from backend.app.models import Scene, DeviceModel, Image, ImagePair
from itertools import combinations
from PIL import Image as PILImage

# 测试数据目录
TEST_DIR = PROJECT_ROOT / "test_images"
MODELS_DIR = TEST_DIR / "models"
IMAGES_DIR = TEST_DIR / "images"

# 场景目录名 -> (显示名, 大类, 子类)
SCENE_NAME_MAP = {
    "scene_park_shade_night": ("公园树荫-夜晚", "公园树荫", "夜晚"),
    "scene_rural_road_night": ("农村道路-夜晚", "农村道路", "夜晚"),
}


def create_tables():
    """建表"""
    print("=" * 60)
    print("[1/5] 创建数据表...")
    try:
        Base.metadata.create_all(bind=engine)
        print("      ✅ 数据表创建/验证成功")
        return True
    except Exception as e:
        print(f"      ❌ 建表失败: {e}")
        return False


def import_models(db):
    """导入机型数据"""
    print("=" * 60)
    print("[2/5] 导入机型数据...")

    if not MODELS_DIR.exists():
        print(f"      ❌ 机型目录不存在: {MODELS_DIR}")
        return {}

    model_files = sorted([
        f for f in MODELS_DIR.iterdir()
        if f.is_file() and f.suffix == '.json'
    ])

    if not model_files:
        print("      ⚠️  未找到机型JSON文件")
        return {}

    device_map = {}  # 设备名 -> DeviceModel 对象
    success = 0
    skip = 0

    for json_file in model_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            device_name = data.get('设备名', '')
            if not device_name:
                print(f"      ⚠️  跳过 {json_file.name}: 缺少设备名")
                continue

            # 检查是否已存在
            existing = db.query(DeviceModel).filter(DeviceModel.name == device_name).first()
            if existing:
                print(f"      ⏭️  机型已存在: {device_name}")
                device_map[device_name] = existing
                skip += 1
                continue

            # 生成 folder_name
            folder_name = device_name.replace(" ", "_").replace("-", "_")

            # 创建机型记录
            model = DeviceModel(
                name=device_name,
                folder_name=folder_name,
                main_chip=data.get('主控型号', ''),
                lens_model=data.get('镜头型号', ''),
                sensor_model=data.get('Sensor型号', ''),
                aperture=data.get('光圈', ''),
                focal_length=data.get('焦距', ''),
                resolution=data.get('分辨率', ''),
                frame_rate=data.get('帧率', ''),
                white_led=data.get('白光灯珠料号', ''),
                ir_led=data.get('红外灯珠料号', ''),
                housing_info=data.get('壳体信息', ''),
                device_attrs={'固件版本': data.get('固件版本', '')},
            )
            db.add(model)
            db.flush()
            device_map[device_name] = model
            success += 1
            print(f"      ➕ 创建机型: {device_name}")

        except Exception as e:
            print(f"      ❌ 处理 {json_file.name} 失败: {e}")

    print(f"      📊 导入完成: 新增 {success}, 跳过 {skip}")
    return device_map


def import_scenes(db):
    """导入场景数据"""
    print("=" * 60)
    print("[3/5] 导入场景数据...")

    if not IMAGES_DIR.exists():
        print(f"      ❌ 图像目录不存在: {IMAGES_DIR}")
        return {}

    scene_dirs = sorted([
        d for d in IMAGES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ])

    if not scene_dirs:
        print("      ⚠️  未找到场景目录")
        return {}

    scene_map = {}  # 目录名 -> Scene 对象
    success = 0
    skip = 0

    for scene_dir in scene_dirs:
        dir_name = scene_dir.name

        # 获取场景显示信息
        scene_info = SCENE_NAME_MAP.get(dir_name)
        if scene_info:
            scene_name, category, subcategory = scene_info
        else:
            # 自动解析：scene_park_shade_night -> 公园树荫-夜晚
            scene_name = dir_name.replace("scene_", "").replace("_", "-")
            parts = scene_name.split('-', 1)
            category = parts[0] if parts else scene_name
            subcategory = parts[1] if len(parts) > 1 else ''

        # 检查是否已存在（通过 folder_name）
        existing = db.query(Scene).filter(Scene.folder_name == dir_name).first()
        if existing:
            print(f"      ⏭️  场景已存在: {scene_name}")
            scene_map[dir_name] = existing
            skip += 1
            continue

        # 创建场景记录
        scene = Scene(
            category=category,
            subcategory=subcategory,
            name=scene_name,
            folder_name=dir_name,
            sort_order=0,
        )
        db.add(scene)
        db.flush()
        scene_map[dir_name] = scene
        success += 1
        print(f"      ➕ 创建场景: {scene_name} ({dir_name})")

    print(f"      📊 导入完成: 新增 {success}, 跳过 {skip}")
    return scene_map


def import_images(db, device_map, scene_map):
    """导入图像数据"""
    print("=" * 60)
    print("[4/5] 导入图像数据...")

    # 建立设备名到机型的反向映射
    name_to_device = {name: device for name, device in device_map.items()}

    total_success = 0
    total_skip = 0
    total_error = 0

    for dir_name, scene in scene_map.items():
        scene_dir = IMAGES_DIR / dir_name
        if not scene_dir.exists():
            print(f"      ⚠️  场景目录不存在: {scene_dir}")
            continue

        print(f"\n      📁 场景: {scene.name} ({dir_name})")

        # 查找该场景下的所有图像文件
        image_files = sorted([
            f for f in scene_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png')
        ])

        for img_file in image_files:
            device_name = img_file.stem  # 文件名（不含扩展名）作为设备名

            # 查找对应的机型
            device = name_to_device.get(device_name)
            if not device:
                print(f"         ⚠️  机型不存在: {device_name}，跳过")
                total_error += 1
                continue

            # 检查是否已存在
            existing = db.query(Image).filter(
                Image.scene_id == scene.id,
                Image.device_id == device.id,
            ).first()
            if existing:
                print(f"         ⏭️  图像已存在: {device_name}")
                total_skip += 1
                continue

            # 读取图像元信息JSON
            json_file = scene_dir / f"{device_name}.json"
            shot_attrs = {}
            env_attrs = {}
            isp_attrs = {}
            note_attrs = {}

            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    # 映射字段
                    if '基础采集信息' in meta:
                        note_attrs = {
                            '采集时间': meta['基础采集信息'].get('采集时间', ''),
                            '采集人员': meta['基础采集信息'].get('采集人员', ''),
                            '采集地点': meta['基础采集信息'].get('采集地点', ''),
                            '采集环境': meta['基础采集信息'].get('采集环境', ''),
                            '设备编号': meta['基础采集信息'].get('设备编号', ''),
                            '采集目的': meta['基础采集信息'].get('采集目的', ''),
                            '特殊说明': meta['基础采集信息'].get('特殊说明', ''),
                        }

                    if '场景信息' in meta:
                        env_attrs = meta['场景信息']

                    if '图像视频参数' in meta:
                        shot_attrs = meta['图像视频参数']
                    elif '图像/视频参数' in meta:
                        shot_attrs = meta['图像/视频参数']

                    if 'ISP参数' in meta:
                        isp_attrs = meta['ISP参数']

                except Exception as e:
                    print(f"         ⚠️  读取JSON失败: {json_file.name} - {e}")

            # 复制图像文件到 uploads 目录
            dest_dir = IMAGE_DIR / scene.folder_name / device.folder_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / img_file.name

            if not dest_file.exists():
                shutil.copy2(img_file, dest_file)

            # 生成缩略图
            thumb_path = ""
            try:
                thumb_dir = THUMB_DIR / scene.folder_name / device.folder_name
                thumb_dir.mkdir(parents=True, exist_ok=True)
                thumb_file = thumb_dir / img_file.name
                if not thumb_file.exists():
                    pil_img = PILImage.open(img_file)
                    pil_img.thumbnail(THUMB_SIZE, PILImage.Resampling.LANCZOS)
                    pil_img.save(thumb_file, quality=85)
                thumb_path = f"/uploads/thumbnails/{scene.folder_name}/{device.folder_name}/{img_file.name}"
            except Exception as e:
                print(f"         ⚠️  缩略图生成失败: {img_file.name} - {e}")

            # 图像URL
            image_url = f"/uploads/images/{scene.folder_name}/{device.folder_name}/{img_file.name}"

            # 创建图像记录
            image = Image(
                scene_id=scene.id,
                device_id=device.id,
                image_path=image_url,
                thumb_path=thumb_path,
                shot_attrs=shot_attrs,
                env_attrs=env_attrs,
                isp_attrs=isp_attrs,
                note_attrs=note_attrs,
            )
            db.add(image)
            total_success += 1
            print(f"         ➕ 录入图像: {device_name}")

    db.flush()
    print(f"\n      📊 导入完成: 新增 {total_success}, 跳过 {total_skip}, 错误 {total_error}")
    return total_success


def generate_pairs(db):
    """生成配对"""
    print("=" * 60)
    print("[5/5] 生成图像配对...")

    scenes = db.query(Scene).all()
    total_new = 0

    for scene in scenes:
        images = db.query(Image).filter(Image.scene_id == scene.id).all()
        if len(images) < 2:
            print(f"      ⚠️  场景 {scene.name} 图像不足2张，跳过")
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
            print(f"      ➕ 场景 {scene.name}: 生成 {new_count} 对新配对")
            total_new += new_count
        else:
            print(f"      ⏭️  场景 {scene.name}: 无新配对")

    print(f"      📊 配对完成: 新增 {total_new} 对")


def main():
    """主函数"""
    print()
    print("🚀 开始批量导入测试数据...")
    print(f"   数据目录: {TEST_DIR}")
    print()

    # 1. 建表
    if not create_tables():
        return

    db = SessionLocal()
    try:
        # 2. 导入机型
        device_map = import_models(db)
        if not device_map:
            print("❌ 无机型数据，终止导入")
            return

        # 3. 导入场景
        scene_map = import_scenes(db)
        if not scene_map:
            print("❌ 无场景数据，终止导入")
            return

        # 4. 导入图像
        import_images(db, device_map, scene_map)

        # 5. 生成配对
        generate_pairs(db)

        # 提交事务
        db.commit()
        print()
        print("=" * 60)
        print("✅ 批量导入完成！")

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print()


if __name__ == "__main__":
    main()
