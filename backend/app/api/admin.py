"""
管理路由：大类/子类/场景/设备/用户 CRUD
"""
import os
import shutil
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..core.config import IMAGE_DIR, THUMB_DIR
from ..core.security import hash_password
from ..models.user import User
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.image import Image
from ..models.image_pair import ImagePair
from ..schemas.scene_category import CategoryCreate, CategoryUpdate, CategoryOut
from ..schemas.scene_subcategory import SubcategoryCreate, SubcategoryUpdate, SubcategoryOut
from ..schemas.scene import SceneCreate, SceneUpdate, SceneOut
from ..schemas.device_model import DeviceModelCreate, DeviceModelUpdate, DeviceModelOut
from ..schemas.auth import AdminUserOut, ResetPasswordRequest

router = APIRouter(prefix="/api/admin", tags=["管理"])


# ==================== 大类管理 ====================

@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    categories = db.query(SceneCategory).order_by(SceneCategory.id).all()
    result = []
    for c in categories:
        scene_count = db.query(Scene).filter(Scene.category_id == c.id).count()
        result.append(CategoryOut(
            id=c.id, name=c.name, location=c.location, scene_count=scene_count,
        ))
    return result


@router.post("/categories", response_model=CategoryOut)
async def create_category(
    body: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SceneCategory).filter(
        SceneCategory.name == body.name,
        SceneCategory.location == body.location,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"大类 '{body.name}({body.location})' 已存在")

    cat = SceneCategory(name=body.name, location=body.location)
    db.add(cat)
    db.commit()
    db.refresh(cat)

    return CategoryOut(
        id=cat.id, name=cat.name, location=cat.location, scene_count=0,
    )


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(SceneCategory).filter(SceneCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="大类不存在")

    if body.name is not None:
        cat.name = body.name
    if body.location is not None:
        cat.location = body.location

    db.commit()
    db.refresh(cat)

    scene_count = db.query(Scene).filter(Scene.category_id == cat.id).count()
    return CategoryOut(
        id=cat.id, name=cat.name, location=cat.location, scene_count=scene_count,
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(SceneCategory).filter(SceneCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="大类不存在")

    scene_count = db.query(Scene).filter(Scene.category_id == cat.id).count()
    if scene_count > 0:
        raise HTTPException(status_code=400, detail=f"该大类下有 {scene_count} 个场景，请先删除场景")

    db.delete(cat)
    db.commit()
    return {"success": True}


# ==================== 子类管理 ====================

@router.get("/subcategories", response_model=list[SubcategoryOut])
async def get_subcategories(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    subcategories = db.query(SceneSubcategory).order_by(SceneSubcategory.id).all()
    result = []
    for s in subcategories:
        scene_count = db.query(Scene).filter(Scene.subcategory_id == s.id).count()
        result.append(SubcategoryOut(
            id=s.id, name=s.name, scene_count=scene_count,
        ))
    return result


@router.post("/subcategories", response_model=SubcategoryOut)
async def create_subcategory(
    body: SubcategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SceneSubcategory).filter(SceneSubcategory.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"子类 '{body.name}' 已存在")

    sub = SceneSubcategory(name=body.name)
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return SubcategoryOut(
        id=sub.id, name=sub.name, scene_count=0,
    )


@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryOut)
async def update_subcategory(
    subcategory_id: int,
    body: SubcategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="子类不存在")

    if body.name is not None:
        sub.name = body.name

    db.commit()
    db.refresh(sub)

    scene_count = db.query(Scene).filter(Scene.subcategory_id == sub.id).count()
    return SubcategoryOut(
        id=sub.id, name=sub.name, scene_count=scene_count,
    )


@router.delete("/subcategories/{subcategory_id}")
async def delete_subcategory(
    subcategory_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="子类不存在")

    scene_count = db.query(Scene).filter(Scene.subcategory_id == sub.id).count()
    if scene_count > 0:
        raise HTTPException(status_code=400, detail=f"该子类下有 {scene_count} 个场景，请先删除场景")

    db.delete(sub)
    db.commit()
    return {"success": True}


# ==================== 场景管理 ====================

@router.get("/scenes", response_model=list[SceneOut])
async def get_scenes(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scenes = db.query(Scene).order_by(Scene.sort_order).all()
    result = []
    for s in scenes:
        image_count = db.query(Image).filter(Image.scene_id == s.id).count()
        pair_count = db.query(ImagePair).filter(ImagePair.scene_id == s.id).count()
        result.append(SceneOut(
            id=s.id,
            category_id=s.category_id,
            category_name=s.category_name,
            location=s.location,
            subcategory_id=s.subcategory_id,
            subcategory_name=s.subcategory_name,
            name=s.name,
            folder_name=s.folder_name,
            sort_order=s.sort_order,
            image_count=image_count,
            pair_count=pair_count,
        ))
    return result


@router.post("/scenes", response_model=SceneOut)
async def create_scene(
    body: SceneCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 校验外键
    cat = db.query(SceneCategory).filter(SceneCategory.id == body.category_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="大类不存在")
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.id == body.subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=400, detail="子类不存在")

    # 校验唯一性
    existing = db.query(Scene).filter(
        Scene.category_id == body.category_id,
        Scene.subcategory_id == body.subcategory_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"场景 '{cat.name}({cat.location})-{sub.name}' 已存在",
        )

    scene = Scene(
        category_id=body.category_id,
        subcategory_id=body.subcategory_id,
        sort_order=body.sort_order,
    )
    db.add(scene)
    db.flush()

    # 建目录（失败则回滚）
    try:
        (IMAGE_DIR / scene.folder_name).mkdir(parents=True, exist_ok=True)
        (THUMB_DIR / scene.folder_name).mkdir(parents=True, exist_ok=True)
    except OSError:
        db.rollback()
        raise HTTPException(status_code=500, detail="创建存储目录失败")

    db.commit()
    db.refresh(scene)

    return SceneOut(
        id=scene.id,
        category_id=scene.category_id,
        category_name=scene.category_name,
        location=scene.location,
        subcategory_id=scene.subcategory_id,
        subcategory_name=scene.subcategory_name,
        name=scene.name,
        folder_name=scene.folder_name,
        sort_order=scene.sort_order,
        image_count=0,
        pair_count=0,
    )


@router.put("/scenes/{scene_id}", response_model=SceneOut)
async def update_scene(
    scene_id: int,
    body: SceneUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    if body.sort_order is not None:
        scene.sort_order = body.sort_order

    db.commit()
    db.refresh(scene)

    image_count = db.query(Image).filter(Image.scene_id == scene.id).count()
    pair_count = db.query(ImagePair).filter(ImagePair.scene_id == scene.id).count()

    return SceneOut(
        id=scene.id,
        category_id=scene.category_id,
        category_name=scene.category_name,
        location=scene.location,
        subcategory_id=scene.subcategory_id,
        subcategory_name=scene.subcategory_name,
        name=scene.name,
        folder_name=scene.folder_name,
        sort_order=scene.sort_order,
        image_count=image_count,
        pair_count=pair_count,
    )


@router.delete("/scenes/{scene_id}")
async def delete_scene(
    scene_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    image_count = db.query(Image).filter(Image.scene_id == scene.id).count()
    if image_count > 0:
        raise HTTPException(status_code=400, detail=f"该场景下有 {image_count} 张图片，请先删除图片")

    # 清理目录
    for base_dir in [IMAGE_DIR, THUMB_DIR]:
        dir_path = base_dir / scene.folder_name
        if dir_path.exists():
            shutil.rmtree(dir_path)

    db.delete(scene)
    db.commit()
    return {"success": True}


# ==================== 设备管理 ====================

def _generate_device_folder(name: str) -> str:
    """从设备名称生成 folder_name"""
    import re
    folder = name.replace(" ", "_")
    folder = re.sub(r'[^a-zA-Z0-9_\-]', '', folder)
    return f"device_{folder}" if folder else "device_unknown"


@router.get("/devices", response_model=list[DeviceModelOut])
async def get_devices(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    devices = db.query(DeviceModel).all()
    result = []
    for d in devices:
        image_count = db.query(Image).filter(Image.device_id == d.id).count()
        result.append(DeviceModelOut(
            id=d.id, name=d.name, folder_name=d.folder_name,
            main_chip=d.main_chip or "", lens_model=d.lens_model or "",
            sensor_model=d.sensor_model or "", aperture=d.aperture or "",
            focal_length=d.focal_length or "", resolution=d.resolution or "",
            frame_rate=d.frame_rate or "", white_led=d.white_led or "",
            ir_led=d.ir_led or "", housing_info=d.housing_info or "",
            device_attrs=d.device_attrs or {}, features=d.features or "",
            image_count=image_count,
        ))
    return result


@router.post("/devices", response_model=DeviceModelOut)
async def create_device(
    body: DeviceModelCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(DeviceModel).filter(DeviceModel.name == body.name).first():
        raise HTTPException(status_code=400, detail=f"设备 '{body.name}' 已存在")

    folder_name = _generate_device_folder(body.name)

    if db.query(DeviceModel).filter(DeviceModel.folder_name == folder_name).first():
        raise HTTPException(status_code=400, detail=f"目录名 '{folder_name}' 已存在")

    device = DeviceModel(
        name=body.name,
        folder_name=folder_name,
        main_chip=body.main_chip,
        lens_model=body.lens_model,
        sensor_model=body.sensor_model,
        aperture=body.aperture,
        focal_length=body.focal_length,
        resolution=body.resolution,
        frame_rate=body.frame_rate,
        white_led=body.white_led,
        ir_led=body.ir_led,
        housing_info=body.housing_info,
        device_attrs=body.device_attrs or {},
        features=body.features or "",
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return DeviceModelOut(
        id=device.id, name=device.name, folder_name=device.folder_name,
        main_chip=device.main_chip or "", lens_model=device.lens_model or "",
        sensor_model=device.sensor_model or "", aperture=device.aperture or "",
        focal_length=device.focal_length or "", resolution=device.resolution or "",
        frame_rate=device.frame_rate or "", white_led=device.white_led or "",
        ir_led=device.ir_led or "", housing_info=device.housing_info or "",
        device_attrs=device.device_attrs or {}, features=device.features or "",
        image_count=0,
    )


@router.put("/devices/{device_id}", response_model=DeviceModelOut)
async def update_device(
    device_id: int,
    body: DeviceModelUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    if body.name is not None:
        existing = db.query(DeviceModel).filter(
            DeviceModel.name == body.name, DeviceModel.id != device_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"设备名 '{body.name}' 已被使用")
        device.name = body.name
        device.folder_name = _generate_device_folder(body.name)

    for field in ["main_chip", "lens_model", "sensor_model", "aperture", "focal_length",
                   "resolution", "frame_rate", "white_led", "ir_led", "housing_info", "features"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(device, field, val)

    if body.device_attrs is not None:
        device.device_attrs = body.device_attrs

    db.commit()
    db.refresh(device)

    image_count = db.query(Image).filter(Image.device_id == device.id).count()

    return DeviceModelOut(
        id=device.id, name=device.name, folder_name=device.folder_name,
        main_chip=device.main_chip or "", lens_model=device.lens_model or "",
        sensor_model=device.sensor_model or "", aperture=device.aperture or "",
        focal_length=device.focal_length or "", resolution=device.resolution or "",
        frame_rate=device.frame_rate or "", white_led=device.white_led or "",
        ir_led=device.ir_led or "", housing_info=device.housing_info or "",
        device_attrs=device.device_attrs or {}, features=device.features or "",
        image_count=image_count,
    )


# ==================== 概览统计 ====================

@router.get("/overview")
async def get_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from ..services.stats_service import get_overview as _get_overview
    return _get_overview(db)


# ==================== 用户管理 ====================

@router.get("/users", response_model=list[AdminUserOut])
async def get_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from ..models.evaluation import Evaluation

    users = db.query(User).order_by(User.id).all()
    result = []
    now = datetime.utcnow()
    for u in users:
        # 统计已提交的评价数量
        evaluation_count = db.query(Evaluation).filter(
            Evaluation.user_id == u.id,
            Evaluation.status == "submitted"
        ).count()

        has_active_reset = (
            u.reset_token is not None
            and u.reset_token_expires is not None
            and u.reset_token_expires > now
        )
        result.append(AdminUserOut(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            display_name=u.display_name or u.username,
            created_at=str(u.created_at) if u.created_at else None,
            last_active_at=str(u.last_active_at) if u.last_active_at else None,
            has_active_reset=has_active_reset,
            evaluation_count=evaluation_count,
        ))
    return result


@router.put("/users/{user_id}/reset-password")
async def trigger_password_reset(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 生成重置令牌（有效期24小时）
    user.reset_token = secrets.token_urlsafe(32)
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()

    reset_link = f"/#/reset-password?token={user.reset_token}"
    return {
        "success": True,
        "reset_link": reset_link,
        "expires_in": "24小时",
        "message": f"请将重置链接发送给用户 {user.username}",
    }
