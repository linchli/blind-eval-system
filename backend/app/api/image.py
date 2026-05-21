"""
图像与配对路由
"""
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..core.config import IMAGE_DIR
from ..models.user import User
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.image import Image
from ..models.image_pair import ImagePair
from ..models.evaluation import Evaluation
from ..schemas.image import (
    ImageOut, PairGenerateRequest, PairGeneratePreview,
    PairGenerateResult, ImagePairOut,
)
from ..schemas.common import ApiResponse
from ..services.image_service import save_image_file, generate_pairs_for_scene, preview_pair_generation

router = APIRouter(prefix="/api/admin", tags=["图像管理"])


# ==================== 图像管理 ====================

@router.get("/images", response_model=list[ImageOut])
async def get_images(
    scene_id: int = None,
    device_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Image)
    if scene_id:
        query = query.filter(Image.scene_id == scene_id)
    if device_id:
        query = query.filter(Image.device_id == device_id)

    images = query.order_by(Image.created_at.desc()).all()
    result = []
    for img in images:
        result.append(ImageOut(
            id=img.id,
            scene_id=img.scene_id,
            device_id=img.device_id,
            scene_name=img.scene.name if img.scene else "",
            device_name=img.device.name if img.device else "",
            image_path=img.image_path,
            thumb_path=img.thumb_path or "",
            shot_attrs=img.shot_attrs or {},
            env_attrs=img.env_attrs or {},
            isp_attrs=img.isp_attrs or {},
            note_attrs=img.note_attrs or {},
        ))
    return result


@router.post("/images", response_model=ImageOut)
async def upload_image(
    scene_id: int = Form(...),
    device_id: int = Form(...),
    shot_attrs: str = Form("{}"),
    env_attrs: str = Form("{}"),
    isp_attrs: str = Form("{}"),
    note_attrs: str = Form("{}"),
    image_file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传图像并录入元数据"""
    # 校验场景和设备
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 唯一约束检查
    existing = db.query(Image).filter(
        Image.scene_id == scene_id, Image.device_id == device_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"该场景已有此设备的图像，禁止重复录入（如需升级固件，请创建新设备后录入）"
        )

    # 解析 JSON 属性
    try:
        shot_attrs_dict = json.loads(shot_attrs) if shot_attrs else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="shot_attrs JSON 格式错误")
    try:
        env_attrs_dict = json.loads(env_attrs) if env_attrs else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="env_attrs JSON 格式错误")
    try:
        isp_attrs_dict = json.loads(isp_attrs) if isp_attrs else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="isp_attrs JSON 格式错误")
    try:
        note_attrs_dict = json.loads(note_attrs) if note_attrs else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="note_attrs JSON 格式错误")

    # 保存文件
    file_content = await image_file.read()
    filename = image_file.filename or "image.jpg"
    image_url, thumb_path = save_image_file(
        file_content, scene.folder_name, device.folder_name, filename
    )

    # 创建记录
    image = Image(
        scene_id=scene_id,
        device_id=device_id,
        image_path=image_url,
        thumb_path=thumb_path,
        shot_attrs=shot_attrs_dict,
        env_attrs=env_attrs_dict,
        isp_attrs=isp_attrs_dict,
        note_attrs=note_attrs_dict,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return ImageOut(
        id=image.id,
        scene_id=image.scene_id,
        device_id=image.device_id,
        scene_name=scene.name,
        device_name=device.name,
        image_path=image.image_path,
        thumb_path=image.thumb_path or "",
        shot_attrs=image.shot_attrs or {},
        env_attrs=image.env_attrs or {},
        isp_attrs=image.isp_attrs or {},
        note_attrs=image.note_attrs or {},
    )


@router.delete("/images/{image_id}", response_model=ApiResponse)
async def delete_image(
    image_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图像不存在")

    # 检查是否已配对
    pair_count = db.query(ImagePair).filter(
        (ImagePair.image_a_id == image_id) | (ImagePair.image_b_id == image_id)
    ).count()
    if pair_count > 0:
        raise HTTPException(status_code=400, detail="该图像已被配对，无法删除")

    db.delete(image)
    db.commit()
    return ApiResponse(success=True, message="图像已删除")


# ==================== 配对管理 ====================

@router.get("/pairs", response_model=list[ImagePairOut])
async def get_pairs(
    scene_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ImagePair)
    if scene_id:
        query = query.filter(ImagePair.scene_id == scene_id)

    pairs = query.order_by(ImagePair.sort_order).all()
    result = []
    for p in pairs:
        eval_count = db.query(Evaluation).filter(
            Evaluation.pair_id == p.id, Evaluation.status == "submitted"
        ).count()

        img_a = p.image_a
        img_b = p.image_b
        device_a_name = img_a.device.name if img_a and img_a.device else ""
        device_b_name = img_b.device.name if img_b and img_b.device else ""
        image_a_url = img_a.image_path if img_a else ""
        image_b_url = img_b.image_path if img_b else ""

        result.append(ImagePairOut(
            id=p.id, scene_id=p.scene_id,
            scene_name=p.scene.name if p.scene else "",
            image_a_id=p.image_a_id, image_b_id=p.image_b_id,
            device_a_name=device_a_name, device_b_name=device_b_name,
            image_a_url=image_a_url, image_b_url=image_b_url,
            sort_order=p.sort_order, eval_count=eval_count,
        ))
    return result


@router.post("/pairs/preview", response_model=PairGeneratePreview)
async def preview_pairs(
    body: PairGenerateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """预览配对生成结果"""
    result = preview_pair_generation(db, body.scene_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return PairGeneratePreview(
        scene_name=result["scene_name"],
        strategy=body.strategy,
        current_image_count=result["current_image_count"],
        total_combinations=result["total_combinations"],
        existing_pair_count=result["existing_pair_count"],
        new_pair_count=result["new_pair_count"],
    )


@router.post("/pairs/generate", response_model=PairGenerateResult)
async def generate_pairs(
    body: PairGenerateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """生成配对"""
    if body.strategy != "full":
        raise HTTPException(status_code=400, detail="目前仅支持全量配对策略")

    result = generate_pairs_for_scene(db, body.scene_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    db.commit()

    return PairGenerateResult(
        scene_name=result["scene_name"],
        strategy=body.strategy,
        new_pairs=result["new_pair_count"],
        total_pairs=result["existing_pair_count"] + result["new_pair_count"],
        message=result["message"],
    )


@router.get("/pairs/scene-stats/{scene_id}")
async def get_scene_pair_stats(
    scene_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取场景配对统计"""
    from ..services.stats_service import get_scene_stats
    return get_scene_stats(db, scene_id)
