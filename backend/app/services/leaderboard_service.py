"""
排行榜服务 — 计算 BT 得分、评分均值，生成筛选组合，写入数据库
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session, aliased
from sqlalchemy import func as sql_func

from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.device_model import DeviceModel
from ..models.leaderboard import LeaderboardRanking
from ..services.cleaning_service import bradley_terry, EvalRecord, get_scene_names
from ..core import config


def load_valid_records(db: Session) -> list[EvalRecord]:
    """加载所有有效评测记录"""
    ImageA = aliased(Image, name="image_a")
    ImageB = aliased(Image, name="image_b")

    rows = (
        db.query(
            Evaluation.id.label("eval_id"),
            Evaluation.user_id,
            Evaluation.pair_id,
            Evaluation.session_id,
            Evaluation.score_a,
            Evaluation.score_b,
            ImagePair.scene_id,
            ImageA.device_id.label("device_a_id"),
            ImageB.device_id.label("device_b_id"),
        )
        .join(ImagePair, Evaluation.pair_id == ImagePair.id)
        .join(ImageA, ImagePair.image_a_id == ImageA.id)
        .join(ImageB, ImagePair.image_b_id == ImageB.id)
        .filter(Evaluation.status == "submitted")
        .filter(Evaluation.is_valid == 1)
        .all()
    )

    records = []
    for row in rows:
        records.append(EvalRecord(
            eval_id=row.eval_id,
            user_id=row.user_id,
            pair_id=row.pair_id,
            session_id=row.session_id,
            scene_id=row.scene_id,
            device_a_id=row.device_a_id,
            device_b_id=row.device_b_id,
            score_a=row.score_a,
            score_b=row.score_b,
        ))

    return records


def compute_leaderboard(db: Session) -> dict:
    """计算排行榜数据并写入数据库。"""
    records = load_valid_records(db)
    if not records:
        return {"total_devices": 0, "records_written": 0}

    scene_names = get_scene_names(db)
    devices = _get_devices(db)

    overall_bt = bradley_terry(records)
    max_bt = max(overall_bt.values()) if overall_bt else 1.0

    scene_ids = {r.scene_id for r in records}
    scene_bt_scores = {}
    for sid in scene_ids:
        scene_bt = bradley_terry(records, scene_id=sid)
        scene_bt_scores[sid] = scene_bt

    device_scores = _compute_mean_scores(records)

    scene_mean_scores = {}
    for sid in scene_ids:
        scene_records = [r for r in records if r.scene_id == sid]
        scene_mean_scores[sid] = _compute_mean_scores(scene_records)

    scene_eval_counts = defaultdict(lambda: defaultdict(int))
    for r in records:
        scene_eval_counts[r.scene_id][r.device_a_id] += 1
        scene_eval_counts[r.scene_id][r.device_b_id] += 1

    now = datetime.now()
    total_devices = len(devices)
    cleaned_record_count = len(records)

    db.query(LeaderboardRanking).delete()

    filter_combinations = _generate_filter_combinations(db)

    records_written = 0
    for filter_type, filter_value, filtered_scene_ids, filtered_device_ids in filter_combinations:
        # 按场景筛选
        if filtered_scene_ids is not None:
            filtered_records = [r for r in records if r.scene_id in filtered_scene_ids]
        else:
            filtered_records = records

        # 按设备参数筛选
        if filtered_device_ids is not None:
            filtered_records = [r for r in filtered_records if r.device_a_id in filtered_device_ids or r.device_b_id in filtered_device_ids]

        if not filtered_records:
            continue

        filtered_scene_bt = bradley_terry(filtered_records)

        if not filtered_scene_bt:
            continue

        max_filtered_bt = max(filtered_scene_bt.values()) if filtered_scene_bt else 1.0
        filtered_mean_scores = _compute_mean_scores(filtered_records)

        sorted_devices = sorted(
            filtered_scene_bt.keys(),
            key=lambda d: -filtered_scene_bt.get(d, 0)
        )

        for rank_pos, device_id in enumerate(sorted_devices, 1):
            device = devices.get(device_id)
            if not device:
                continue

            bt_score = (filtered_scene_bt.get(device_id, 0) / max_filtered_bt) * 100 if max_filtered_bt > 0 else 0
            mean_score = filtered_mean_scores.get(device_id, 0)

            dev_scene_scores = {}
            for sid in scene_ids:
                if sid in scene_bt_scores and device_id in scene_bt_scores[sid]:
                    sid_bt = scene_bt_scores[sid]
                    max_sid_bt = max(sid_bt.values()) if sid_bt else 1.0
                    dev_scene_scores[scene_names.get(sid, f"场景{sid}")] = {
                        "bt_score": round((sid_bt.get(device_id, 0) / max_sid_bt) * 100, 1) if max_sid_bt > 0 else 0,
                        "mean_score": round(scene_mean_scores.get(sid, {}).get(device_id, 0), 1),
                        "eval_count": scene_eval_counts.get(sid, {}).get(device_id, 0),
                    }

            bt_ranked = sorted(filtered_scene_bt.keys(), key=lambda d: -filtered_scene_bt.get(d, 0))
            mean_ranked = sorted(filtered_mean_scores.keys(), key=lambda d: -filtered_mean_scores.get(d, 0))

            bt_rank = bt_ranked.index(device_id) + 1 if device_id in bt_ranked else 0
            mean_rank = mean_ranked.index(device_id) + 1 if device_id in mean_ranked else 0

            ranking = LeaderboardRanking(
                filter_type=filter_type,
                filter_value=filter_value,
                device_id=device_id,
                device_name=device.name,
                main_chip=device.main_chip or "",
                sensor_model=device.sensor_model or "",
                focal_length=device.focal_length or "",
                resolution=device.resolution or "",
                device_attrs=device.device_attrs,
                bt_score=round(bt_score, 2),
                mean_score=round(mean_score, 2),
                rank_position=rank_pos,
                scene_scores=dev_scene_scores,
                total_devices=total_devices,
                cleaned_record_count=cleaned_record_count,
                last_cleaned_at=now,
            )
            db.add(ranking)
            records_written += 1

    db.commit()

    return {
        "total_devices": total_devices,
        "records_written": records_written,
    }


def _compute_mean_scores(records: list[EvalRecord]) -> dict[int, float]:
    """计算每个设备的评分均值"""
    scores = defaultdict(list)
    for r in records:
        scores[r.device_a_id].append(r.score_a)
        scores[r.device_b_id].append(r.score_b)
    return {d: sum(s) / len(s) for d, s in scores.items()}


def _get_devices(db: Session) -> dict[int, DeviceModel]:
    """获取所有设备"""
    devices = db.query(DeviceModel).all()
    return {d.id: d for d in devices}


def _generate_filter_combinations(db: Session) -> list[tuple[str, Optional[str], Optional[set[int]], Optional[set[int]]]]:
    """生成所有筛选组合。

    返回: [(filter_type, filter_value, scene_ids_or_None, device_ids_or_None), ...]
    scene_ids_or_None 为 None 表示使用所有场景
    device_ids_or_None 为 None 表示使用所有设备
    """
    combinations = []

    combinations.append(("overall", None, None, None))

    categories = db.query(SceneCategory).all()
    for cat in categories:
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.category_id == cat.id).all()}
        if scene_ids:
            combinations.append(("category", cat.name, scene_ids, None))

    locations = {cat.location for cat in categories if cat.location}
    for loc in locations:
        scene_ids = {s.id for s in db.query(Scene).join(SceneCategory).filter(SceneCategory.location == loc).all()}
        if scene_ids:
            combinations.append(("location", loc, scene_ids, None))

    subcategories = db.query(SceneSubcategory).all()
    for sub in subcategories:
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.subcategory_id == sub.id).all()}
        if scene_ids:
            combinations.append(("subcategory", sub.name, scene_ids, None))

    scenes = db.query(Scene).all()
    for scene in scenes:
        combinations.append(("scene", str(scene.id), {scene.id}, None))

    # 设备参数筛选：需要同时记录匹配的设备ID
    devices = db.query(DeviceModel).all()
    chips = {d.main_chip for d in devices if d.main_chip}
    for chip in chips:
        device_ids = {d.id for d in devices if d.main_chip == chip}
        combinations.append(("chip", chip, None, device_ids))

    sensors = {d.sensor_model for d in devices if d.sensor_model}
    for sensor in sensors:
        device_ids = {d.id for d in devices if d.sensor_model == sensor}
        combinations.append(("sensor", sensor, None, device_ids))

    focal_lengths = {d.focal_length for d in devices if d.focal_length}
    for fl in focal_lengths:
        device_ids = {d.id for d in devices if d.focal_length == fl}
        combinations.append(("focal_length", fl, None, device_ids))

    resolutions = {d.resolution for d in devices if d.resolution}
    for res in resolutions:
        device_ids = {d.id for d in devices if d.resolution == res}
        combinations.append(("resolution", res, None, device_ids))

    return combinations


def get_leaderboard(db: Session, filter_type: str, filter_value: Optional[str], score_type: str) -> dict:
    """获取排行榜数据"""
    query = db.query(LeaderboardRanking).filter(
        LeaderboardRanking.filter_type == filter_type,
    )

    if filter_value is not None:
        query = query.filter(LeaderboardRanking.filter_value == filter_value)
    else:
        query = query.filter(LeaderboardRanking.filter_value.is_(None))

    if score_type == "mean":
        query = query.order_by(LeaderboardRanking.mean_score.desc())
    else:
        query = query.order_by(LeaderboardRanking.rank_position.asc())

    rankings = query.all()

    ranking_list = []

    # 按 BT 和均值分别计算排名
    bt_ranked_ids = [r.device_id for r in sorted(rankings, key=lambda x: -(x.bt_score or 0))]
    mean_ranked_ids = [r.device_id for r in sorted(rankings, key=lambda x: -(x.mean_score or 0))]

    # 根据 score_type 确定排序后的排名
    if score_type == "mean":
        sorted_rankings = sorted(rankings, key=lambda x: -(x.mean_score or 0))
    else:
        sorted_rankings = sorted(rankings, key=lambda x: -(x.bt_score or 0))

    for rank_pos, r in enumerate(sorted_rankings, 1):
        bt_rank = bt_ranked_ids.index(r.device_id) + 1 if r.device_id in bt_ranked_ids else 0
        mean_rank = mean_ranked_ids.index(r.device_id) + 1 if r.device_id in mean_ranked_ids else 0

        ranking_list.append({
            "rank": rank_pos,
            "device_id": r.device_id,
            "device_name": r.device_name or "",
            "main_chip": r.main_chip or "",
            "sensor_model": r.sensor_model or "",
            "focal_length": r.focal_length or "",
            "resolution": r.resolution or "",
            "bt_score": r.bt_score or 0,
            "mean_score": r.mean_score or 0,
            "bt_rank": bt_rank,
            "mean_rank": mean_rank,
            "rank_diff": bt_rank - mean_rank,
            "scene_scores": r.scene_scores or {},
        })

    last_updated = None
    if rankings:
        last_updated = rankings[0].last_cleaned_at.isoformat() if rankings[0].last_cleaned_at else None

    return {
        "ranking": ranking_list,
        "filter_info": {"type": filter_type, "value": filter_value},
        "total_devices": rankings[0].total_devices if rankings else 0,
        "last_updated": last_updated,
    }


def get_filter_options(db: Session) -> dict:
    """获取可用的筛选选项"""
    categories = db.query(SceneCategory).all()
    subcategories = db.query(SceneSubcategory).all()
    scenes = db.query(Scene).all()

    locations = sorted({c.location for c in categories if c.location})

    chips = sorted({d.main_chip for d in db.query(DeviceModel).all() if d.main_chip})
    sensors = sorted({d.sensor_model for d in db.query(DeviceModel).all() if d.sensor_model})
    focal_lengths = sorted({d.focal_length for d in db.query(DeviceModel).all() if d.focal_length})
    resolutions = sorted({d.resolution for d in db.query(DeviceModel).all() if d.resolution})

    scene_names = get_scene_names(db)

    return {
        "categories": [{"id": c.id, "name": c.name, "location": c.location} for c in categories],
        "subcategories": [{"id": s.id, "name": s.name} for s in subcategories],
        "scenes": [{"id": s.id, "name": scene_names.get(s.id, f"场景{s.id}")} for s in scenes],
        "locations": locations,
        "chips": chips,
        "sensors": sensors,
        "focal_lengths": focal_lengths,
        "resolutions": resolutions,
    }


def get_leaderboard_details(db: Session, view_type: str, id: int) -> dict:
    """获取详细评测数据（管理员权限）"""
    scene_names = get_scene_names(db)

    if view_type == "scene":
        return _get_scene_details(db, id, scene_names)
    elif view_type == "user":
        return _get_user_details(db, id, scene_names)
    elif view_type == "device":
        return _get_device_details(db, id, scene_names)
    else:
        return {"view_type": view_type, "error": "不支持的视图类型"}


def _get_scene_details(db: Session, scene_id: int, scene_names: dict) -> dict:
    """获取场景详情"""
    from ..models.user import User

    total = db.query(Evaluation).join(ImagePair).filter(ImagePair.scene_id == scene_id).count()
    valid = db.query(Evaluation).join(ImagePair).filter(
        ImagePair.scene_id == scene_id, Evaluation.is_valid == 1
    ).count()
    invalid = db.query(Evaluation).join(ImagePair).filter(
        ImagePair.scene_id == scene_id, Evaluation.is_valid == 0
    ).count()

    # 获取无效用户ID列表
    invalid_user_rows = (
        db.query(Evaluation.user_id)
        .join(ImagePair)
        .filter(ImagePair.scene_id == scene_id, Evaluation.is_valid == 0)
        .distinct()
        .all()
    )
    invalid_user_ids = [u[0] for u in invalid_user_rows]

    # 查询用户名
    invalid_users = []
    if invalid_user_ids:
        users = db.query(User).filter(User.id.in_(invalid_user_ids)).all()
        invalid_users = [{"id": u.id, "username": u.username, "display_name": u.display_name or u.username} for u in users]

    # 从排行榜表获取设备排名
    rankings = (
        db.query(LeaderboardRanking)
        .filter(LeaderboardRanking.filter_type == "scene")
        .filter(LeaderboardRanking.filter_value == str(scene_id))
        .order_by(LeaderboardRanking.rank_position.asc())
        .all()
    )

    # 计算BT排名和均值排名
    bt_ranked = sorted(rankings, key=lambda x: -(x.bt_score or 0))
    mean_ranked = sorted(rankings, key=lambda x: -(x.mean_score or 0))

    device_ranking = []
    for r in rankings:
        # 从 scene_scores JSON 中获取该场景的实际评测次数
        scene_scores = r.scene_scores or {}
        scene_name = scene_names.get(scene_id, f"场景{scene_id}")
        eval_count = 0
        if scene_name in scene_scores:
            eval_count = scene_scores[scene_name].get("eval_count", 0)
        elif str(scene_id) in scene_scores:
            eval_count = scene_scores[str(scene_id)].get("eval_count", 0)

        bt_rank = next((i + 1 for i, x in enumerate(bt_ranked) if x.device_id == r.device_id), 0)
        mean_rank = next((i + 1 for i, x in enumerate(mean_ranked) if x.device_id == r.device_id), 0)

        device_ranking.append({
            "rank": r.rank_position,
            "device_id": r.device_id,
            "device_name": r.device_name or "",
            "eval_count": eval_count,
            "mean_score": r.mean_score or 0,
            "bt_strength": r.bt_score or 0,
            "bt_rank": bt_rank,
            "mean_rank": mean_rank,
            "rank_diff": bt_rank - mean_rank,
        })

    return {
        "view_type": "scene",
        "scene": {
            "id": scene_id,
            "name": scene_names.get(scene_id, f"场景{scene_id}"),
            "total_records": total,
            "valid_records": valid,
            "invalid_records": invalid,
            "invalid_users": invalid_users,
        },
        "device_ranking": device_ranking,
        "invalid_users_by_scene": [],
    }


def _get_user_details(db: Session, user_id: int, scene_names: dict) -> dict:
    """获取用户详情"""
    from ..models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"view_type": "user", "user": {}, "scene_details": []}

    total_evals = db.query(Evaluation).filter(Evaluation.user_id == user_id).count()
    first_evals = db.query(Evaluation).filter(
        Evaluation.user_id == user_id, Evaluation.is_repeat == 0
    ).count()
    retest_evals = db.query(Evaluation).filter(
        Evaluation.user_id == user_id, Evaluation.is_repeat == 1
    ).count()

    scene_details = []
    scenes = db.query(Scene).all()

    passed_scenes = 0
    rejected_scenes = 0

    for scene in scenes:
        eval_count = (
            db.query(Evaluation)
            .join(ImagePair)
            .filter(Evaluation.user_id == user_id, ImagePair.scene_id == scene.id)
            .count()
        )
        if eval_count > 0:
            # 查询该用户在该场景的所有记录（包括通过和拒绝的）
            scene_evals = (
                db.query(Evaluation)
                .join(ImagePair)
                .filter(
                    Evaluation.user_id == user_id,
                    ImagePair.scene_id == scene.id,
                )
                .all()
            )

            # 查找被拒绝的记录
            rejected_eval = next((e for e in scene_evals if e.is_valid == 0), None)
            is_passed = rejected_eval is None

            if is_passed:
                passed_scenes += 1
            else:
                rejected_scenes += 1

            # 从 reject_detail 中获取一致性得分
            retest_agreement_score = 0.0
            retest_agreement_threshold = 0.70
            if rejected_eval and rejected_eval.reject_detail:
                detail = rejected_eval.reject_detail
                retest_agreement_score = detail.get("retest_agreement_score", 0.0)
                retest_agreement_threshold = detail.get("retest_agreement_threshold", 0.70)
            elif is_passed:
                # 对于通过的场景，尝试从任意记录的 reject_detail 获取阈值信息
                # 通过的场景没有 reject_detail，使用默认阈值
                retest_agreement_threshold = 0.70
                # 标记为通过，得分设为阈值（表示至少达到阈值）
                retest_agreement_score = retest_agreement_threshold

            scene_details.append({
                "scene_id": scene.id,
                "scene_name": scene_names.get(scene.id, f"场景{scene.id}"),
                "eval_count": eval_count,
                "retest_agreement_score": retest_agreement_score,
                "retest_agreement_threshold": retest_agreement_threshold,
                "passed": is_passed,
            })

    return {
        "view_type": "user",
        "user": {
            "id": user_id,
            "username": user.username,
            "display_name": user.display_name or user.username,
            "total_evals": total_evals,
            "first_evals": first_evals,
            "retest_evals": retest_evals,
            "retest_rate": retest_evals / total_evals if total_evals > 0 else 0,
            "passed_scenes": passed_scenes,
            "rejected_scenes": rejected_scenes,
            "pass_rate": passed_scenes / (passed_scenes + rejected_scenes) if (passed_scenes + rejected_scenes) > 0 else 1.0,
        },
        "scene_details": scene_details,
    }


def _get_device_details(db: Session, device_id: int, scene_names: dict) -> dict:
    """获取设备详情"""
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        return {"view_type": "device", "device": {}, "scenes": []}

    rankings = (
        db.query(LeaderboardRanking)
        .filter(LeaderboardRanking.filter_type == "scene")
        .filter(LeaderboardRanking.device_id == device_id)
        .all()
    )

    scenes = []
    for r in rankings:
        scene_id = int(r.filter_value) if r.filter_value else 0
        scene_name = scene_names.get(scene_id, f"场景{scene_id}") if r.filter_value else ""

        # 从 scene_scores JSON 中获取该场景的实际评测次数
        scene_scores = r.scene_scores or {}
        eval_count = 0
        if scene_name in scene_scores:
            eval_count = scene_scores[scene_name].get("eval_count", 0)
        elif str(scene_id) in scene_scores:
            eval_count = scene_scores[str(scene_id)].get("eval_count", 0)

        scenes.append({
            "scene_id": scene_id,
            "scene_name": scene_name,
            "bt_score": r.bt_score or 0,
            "mean_score": r.mean_score or 0,
            "eval_count": eval_count,
        })

    return {
        "view_type": "device",
        "device": {
            "id": device.id,
            "name": device.name,
        },
        "scenes": scenes,
    }


def get_users_list(db: Session) -> list[dict]:
    """获取用户列表（用于详细数据按用户筛选）"""
    from ..models.user import User
    users = db.query(User).filter(User.role != "guest").all()
    return [{"id": u.id, "username": u.username, "display_name": u.display_name or u.username} for u in users]


def export_leaderboard(db: Session, export_type: str, filter_type: str, filter_value: Optional[str], view_type: Optional[str] = None) -> str:
    """导出排行榜数据

    Args:
        export_type: ranking 或 detail
        filter_type: 筛选类型
        filter_value: 筛选值
        view_type: 详细数据的视图类型 (scene/user/device)，None 表示全部
    """
    if export_type == "ranking":
        data = get_leaderboard(db, filter_type, filter_value, "bt")
        lines = [
            "=" * 60,
            f"排行榜数据 - 筛选: {filter_type}={filter_value or '全部'}",
            "=" * 60,
            "",
            f"{'排名':<6}{'设备名':<20}{'主芯片':<15}{'Sensor':<10}{'BT得分':<10}{'均值':<10}",
            "-" * 70,
        ]
        for item in data["ranking"]:
            lines.append(
                f"{item['rank']:<6}{item['device_name']:<20}{item['main_chip']:<15}"
                f"{item['sensor_model']:<10}{item['bt_score']:<10}{item['mean_score']:<10}"
            )
        return "\n".join(lines)

    elif export_type == "detail":
        scene_names = get_scene_names(db)
        lines = [
            "=" * 60,
            "详细评测数据",
            "=" * 60,
            "",
        ]

        # 按场景导出
        if view_type is None or view_type == "scene":
            lines.append("【按场景查看】")
            lines.append("=" * 60)

            scenes = db.query(Scene).all()
            for scene in scenes:
                scene_name = scene_names.get(scene.id, f"场景{scene.id}")
                lines.append(f"\n场景: {scene_name}")
                lines.append("-" * 40)

                # 场景统计
                total = db.query(Evaluation).join(ImagePair).filter(ImagePair.scene_id == scene.id).count()
                valid = db.query(Evaluation).join(ImagePair).filter(
                    ImagePair.scene_id == scene.id, Evaluation.is_valid == 1
                ).count()
                invalid = total - valid
                lines.append(f"总记录: {total}  有效: {valid}  剔除: {invalid}")

                # 剔除用户
                invalid_user_rows = (
                    db.query(Evaluation.user_id)
                    .join(ImagePair)
                    .filter(ImagePair.scene_id == scene.id, Evaluation.is_valid == 0)
                    .distinct()
                    .all()
                )
                if invalid_user_rows:
                    from ..models.user import User
                    invalid_user_ids = [u[0] for u in invalid_user_rows]
                    users = db.query(User).filter(User.id.in_(invalid_user_ids)).all()
                    user_names = [u.display_name or u.username for u in users]
                    lines.append(f"剔除用户: {', '.join(user_names)}")

                # 设备排名
                rankings = (
                    db.query(LeaderboardRanking)
                    .filter(LeaderboardRanking.filter_type == "scene")
                    .filter(LeaderboardRanking.filter_value == str(scene.id))
                    .order_by(LeaderboardRanking.rank_position.asc())
                    .all()
                )

                if rankings:
                    lines.append(f"\n{'排名':<6}{'设备名':<25}{'评测次数':<10}{'评分均值':<10}{'BT强度':<10}")
                    lines.append("-" * 61)
                    for r in rankings:
                        scene_scores = r.scene_scores or {}
                        eval_count = scene_scores.get(scene_name, {}).get("eval_count", 0)
                        lines.append(
                            f"{r.rank_position:<6}{r.device_name or '':<25}"
                            f"{eval_count:<10}{r.mean_score or 0:<10.1f}{r.bt_score or 0:<10.2f}"
                        )
                else:
                    lines.append("暂无数据")

                lines.append("")

        # 按用户导出
        if view_type is None or view_type == "user":
            lines.append("\n【按用户查看】")
            lines.append("=" * 60)

            from ..models.user import User
            users = db.query(User).filter(User.role != "guest").all()

            for user in users:
                total_evals = db.query(Evaluation).filter(Evaluation.user_id == user.id).count()
                if total_evals == 0:
                    continue

                first_evals = db.query(Evaluation).filter(
                    Evaluation.user_id == user.id, Evaluation.is_repeat == 0
                ).count()
                retest_evals = total_evals - first_evals

                lines.append(f"\n用户: {user.display_name or user.username} (ID: {user.id})")
                lines.append("-" * 40)
                lines.append(f"总评测: {total_evals}  首次: {first_evals}  重测: {retest_evals}  重测率: {retest_evals * 100 // total_evals if total_evals > 0 else 0}%")

                # 各场景一致性
                scenes = db.query(Scene).all()
                passed = 0
                rejected = 0
                lines.append(f"\n{'场景':<30}{'评测对数':<10}{'一致性得分':<12}{'阈值':<8}{'状态':<8}")
                lines.append("-" * 68)

                for scene in scenes:
                    eval_count = (
                        db.query(Evaluation)
                        .join(ImagePair)
                        .filter(Evaluation.user_id == user.id, ImagePair.scene_id == scene.id)
                        .count()
                    )
                    if eval_count == 0:
                        continue

                    scene_name = scene_names.get(scene.id, f"场景{scene.id}")
                    rejected_eval = (
                        db.query(Evaluation)
                        .join(ImagePair)
                        .filter(
                            Evaluation.user_id == user.id,
                            ImagePair.scene_id == scene.id,
                            Evaluation.is_valid == 0,
                        )
                        .first()
                    )

                    is_passed = rejected_eval is None
                    if is_passed:
                        passed += 1
                    else:
                        rejected += 1

                    agreement_score = 0.0
                    threshold = 0.70
                    if rejected_eval and rejected_eval.reject_detail:
                        agreement_score = rejected_eval.reject_detail.get("retest_agreement_score", 0.0)
                        threshold = rejected_eval.reject_detail.get("retest_agreement_threshold", 0.70)
                    elif is_passed:
                        agreement_score = threshold

                    status = "✓ 通过" if is_passed else "✗ 拒绝"
                    lines.append(f"{scene_name:<30}{eval_count:<10}{agreement_score:<12.2f}{threshold:<8.2f}{status:<8}")

                lines.append(f"通过场景: {passed}  拒绝场景: {rejected}  通过率: {passed * 100 // (passed + rejected) if (passed + rejected) > 0 else 100}%")
                lines.append("")

        # 按设备导出
        if view_type is None or view_type == "device":
            lines.append("\n【按设备查看】")
            lines.append("=" * 60)

            devices = db.query(DeviceModel).all()
            for device in devices:
                rankings = (
                    db.query(LeaderboardRanking)
                    .filter(LeaderboardRanking.filter_type == "scene")
                    .filter(LeaderboardRanking.device_id == device.id)
                    .all()
                )
                if not rankings:
                    continue

                lines.append(f"\n设备: {device.name} (ID: {device.id})")
                lines.append(f"芯片: {device.main_chip}  Sensor: {device.sensor_model}  焦距: {device.focal_length}  分辨率: {device.resolution}")
                lines.append("-" * 40)

                lines.append(f"{'场景':<30}{'BT得分':<10}{'评分均值':<10}{'评测次数':<10}")
                lines.append("-" * 60)

                for r in rankings:
                    scene_id = int(r.filter_value) if r.filter_value else 0
                    scene_name = scene_names.get(scene_id, f"场景{scene_id}")
                    scene_scores = r.scene_scores or {}
                    eval_count = scene_scores.get(scene_name, {}).get("eval_count", 0)
                    lines.append(
                        f"{scene_name:<30}{r.bt_score or 0:<10.1f}{r.mean_score or 0:<10.1f}{eval_count:<10}"
                    )

                lines.append("")

        return "\n".join(lines)

    else:
        return "暂不支持此导出类型"
