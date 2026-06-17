"""
数据清洗服务 — 合并自 cleaner.py + statistics.py

包含：
1. 单用户一致性检验（重测信度）- 加权 Agreement
2. 用户组一致性检验 - log BT Pearson r
3. Bradley-Terry 模型计算
4. 统计工具函数
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
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
from ..models.user import User
from ..schemas.cleaning import (
    CleaningParams,
    EvalRecord,
    RetestSceneDetail,
    UserGroupSceneDetail,
    RejectType,
)
from ..core import config
from ..core.config import UPLOAD_DIR

try:
    from scipy.stats import pearsonr as scipy_pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# 清洗元数据文件路径（使用项目的 uploads 目录）
_CLEANING_META_PATH = UPLOAD_DIR / "cleaning_meta.json"


# ═══════════════════════════════════════════════════════════════════════════════
# 清洗元数据管理
# ═══════════════════════════════════════════════════════════════════════════════

def _save_cleaning_meta(data: dict) -> None:
    """保存清洗元数据到文件"""
    _CLEANING_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CLEANING_META_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_cleaning_meta() -> dict:
    """加载清洗元数据"""
    if not _CLEANING_META_PATH.exists():
        return {}
    try:
        with open(_CLEANING_META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# 统计工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def pearson_correlation(x: list[float], y: list[float], min_devices: int = 2) -> Optional[float]:
    """Pearson 相关系数。返回 None 表示数据不足或方差为零。"""
    if len(x) < min_devices or len(y) < min_devices:
        return None
    if len(x) != len(y):
        return None

    x_std = _std(x)
    y_std = _std(y)
    if x_std == 0.0 or y_std == 0.0:
        return None

    if HAS_SCIPY:
        r, _ = scipy_pearsonr(x, y)
        return float(r)
    else:
        n = len(x)
        mx, my = _mean(x), _mean(y)
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        denom = (sum((v - mx) ** 2 for v in x) * sum((v - my) ** 2 for v in y)) ** 0.5
        if denom == 0:
            return None
        return cov / denom


def bradley_terry(
    records: list[EvalRecord],
    scene_id: int | None = None,
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> dict[int, float]:
    """
    Bradley-Terry 模型强度估计 (MM 算法)。
    映射: score_a > score_b → A 胜; score_a < score_b → B 胜; 相等 → 平局 (各计 0.5 胜)。
    返回 {device_id: strength}, 几何均值归一化为 1。
    """
    recs = [r for r in records if scene_id is None or r.scene_id == scene_id]

    wins: dict[int, float] = defaultdict(float)
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)

    for r in recs:
        a, b = r.device_a_id, r.device_b_id
        pair_counts[(min(a, b), max(a, b))] += 1

        if r.score_a > r.score_b:
            wins[a] += 1.0
        elif r.score_b > r.score_a:
            wins[b] += 1.0
        else:
            wins[a] += 0.5
            wins[b] += 0.5

    device_ids = sorted(set(
        d for r in recs for d in (r.device_a_id, r.device_b_id)
    ))
    n = len(device_ids)
    if n < 2:
        return {d: 1.0 for d in device_ids}

    theta = {d: 1.0 for d in device_ids}

    for _ in range(max_iter):
        new_theta = {}
        for i in device_ids:
            denominator = 0.0
            for j in device_ids:
                if i == j:
                    continue
                n_ij = pair_counts.get((min(i, j), max(i, j)), 0)
                if n_ij > 0:
                    denominator += n_ij / (theta[i] + theta[j])
            if denominator > 0:
                new_theta[i] = wins[i] / denominator
            else:
                new_theta[i] = 0.0

        log_sum = sum(math.log(max(t, 1e-12)) for t in new_theta.values() if t > 0)
        if log_sum == 0:
            break
        norm = math.exp(log_sum / n)
        for d in device_ids:
            new_theta[d] /= norm

        max_diff = max(abs(new_theta[d] - theta[d]) for d in device_ids)
        theta = new_theta
        if max_diff < tol:
            break

    return dict(theta)


# ── 加权 Agreement 相关 ──────────────────────────────────────────────────────

def _to_judgment_level(score_a: float, score_b: float) -> int:
    """将原始评分映射为 5 级判定方向"""
    if score_a == 2 and score_b == 0:
        return +2
    if score_a == 1 and score_b == 0:
        return +1
    if score_a == 0.5 and score_b == 0.5:
        return 0
    if score_a == 0 and score_b == 1:
        return -1
    if score_a == 0 and score_b == 2:
        return -2
    diff = score_a - score_b
    if diff > 0:
        return min(int(diff), 2)
    elif diff < 0:
        return max(int(diff), -2)
    return 0


_JUDGMENT_WEIGHTS = [
    [ 1.00,  0.70,  0.20, -0.30, -1.00],
    [ 0.70,  1.00,  0.50, -0.30, -0.60],
    [ 0.20,  0.50,  1.00,  0.50,  0.20],
    [-0.60, -0.30,  0.50,  1.00,  0.70],
    [-1.00, -0.60,  0.20,  0.70,  1.00],
]


def weighted_agreement_for_pair(
    score_a_orig: float, score_b_orig: float,
    score_a_retest: float, score_b_retest: float,
) -> float:
    """对单个复评对计算加权一致性得分, 范围 [-1, +1]"""
    d_orig = _to_judgment_level(score_a_orig, score_b_orig)
    d_retest = _to_judgment_level(score_a_retest, score_b_retest)
    return _JUDGMENT_WEIGHTS[d_orig + 2][d_retest + 2]


def scene_weighted_agreement(
    orig_records: list[EvalRecord],
    retest_records: list[EvalRecord],
) -> tuple[float, int]:
    """逐对匹配原始和复评记录, 计算场景级加权一致性得分。"""
    orig_by_pair = {r.pair_id: r for r in orig_records}
    retest_by_pair = {r.pair_id: r for r in retest_records}

    weights = []
    for pair_id, orig_r in orig_by_pair.items():
        retest_r = retest_by_pair.get(pair_id)
        if retest_r is None:
            continue
        w = weighted_agreement_for_pair(
            orig_r.score_a, orig_r.score_b,
            retest_r.score_a, retest_r.score_b,
        )
        weights.append(w)

    if not weights:
        return 0.0, 0

    mean_w = sum(weights) / len(weights)
    return (mean_w + 1.0) / 2.0, len(weights)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════════════════════════

def load_eval_records(db: Session) -> list[EvalRecord]:
    """从数据库加载所有 submitted 状态的评测记录，转换为 EvalRecord"""
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
            Evaluation.is_repeat,
            ImagePair.scene_id,
            ImageA.device_id.label("device_a_id"),
            ImageB.device_id.label("device_b_id"),
        )
        .join(ImagePair, Evaluation.pair_id == ImagePair.id)
        .join(ImageA, ImagePair.image_a_id == ImageA.id)
        .join(ImageB, ImagePair.image_b_id == ImageB.id)
        .filter(Evaluation.status == "submitted")
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


def get_scene_names(db: Session) -> dict[int, str]:
    """获取所有场景名称映射"""
    scenes = (
        db.query(
            Scene.id,
            SceneCategory.name.label("cat_name"),
            SceneCategory.location,
            SceneSubcategory.name.label("sub_name"),
        )
        .join(SceneCategory, Scene.category_id == SceneCategory.id)
        .join(SceneSubcategory, Scene.subcategory_id == SceneSubcategory.id)
        .all()
    )
    result = {}
    for s in scenes:
        cat_part = s.cat_name
        if s.location:
            cat_part = f"{cat_part}({s.location})"
        name = f"{cat_part}-{s.sub_name}" if s.sub_name else cat_part
        result[s.id] = name
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 单用户一致性检验（重测信度）
# ═══════════════════════════════════════════════════════════════════════════════

def split_retest_pairs(
    data: list[EvalRecord],
) -> tuple[list[EvalRecord], list[EvalRecord], int]:
    """分离原始评分和复评数据"""
    groups: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in data:
        groups[(r.user_id, r.pair_id)].append(r)

    original: list[EvalRecord] = []
    retest: list[EvalRecord] = []
    retest_count = 0

    for (uid, pid), recs in groups.items():
        recs.sort(key=lambda r: r.eval_id)
        original.append(recs[0])
        if len(recs) >= 2:
            retest_count += 1
            retest.append(recs[1])
        for r in recs[2:]:
            retest.append(r)

    return original, retest, retest_count


def clean_single_user_consistency(
    data: list[EvalRecord],
    params: CleaningParams,
    scene_names: dict[int, str],
) -> dict:
    """
    重测信度检验 (单用户自评一致性) — 加权 Agreement。
    返回: {user_id: {scene_details: [...], rejected_scenes: set, ...}}
    """
    result = {}
    user_groups: dict[int, list[EvalRecord]] = defaultdict(list)
    for r in data:
        user_groups[r.user_id].append(r)

    for user_id, user_data in user_groups.items():
        original, retest, retest_count = split_retest_pairs(user_data)
        total_pairs = len({(r.user_id, r.pair_id) for r in user_data})
        required_retest = int(total_pairs * params.retest_ratio)

        if retest_count < required_retest:
            result[user_id] = {
                "scene_details": [],
                "rejected_scenes": {r.scene_id for r in user_data},
                "insufficient_retest": True,
                "retest_info": {
                    "retest_count": retest_count,
                    "total_pairs": total_pairs,
                    "required_retest": required_retest,
                },
            }
            continue

        scene_details = []
        rejected_scenes = set()

        original_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
        retest_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
        for r in original:
            original_by_scene[r.scene_id].append(r)
        for r in retest:
            retest_by_scene[r.scene_id].append(r)

        all_scenes = sorted(set(original_by_scene.keys()) | set(retest_by_scene.keys()))

        for scene_id in all_scenes:
            orig_recs = original_by_scene.get(scene_id, [])
            retest_recs = retest_by_scene.get(scene_id, [])
            agreement_score, matched_pairs = scene_weighted_agreement(orig_recs, retest_recs)

            if matched_pairs == 0:
                rejected = True
            elif agreement_score >= params.retest_agreement_threshold:
                rejected = False
            elif agreement_score < params.retest_hard_reject_threshold:
                rejected = True
            else:
                rejected = True  # 灰色地带

            scene_details.append(RetestSceneDetail(
                scene_id=scene_id,
                scene_name=scene_names.get(scene_id, f"场景{scene_id}"),
                retest_agreement_score=round(agreement_score, 4),
                retest_agreement_threshold=params.retest_agreement_threshold,
                retest_hard_reject_threshold=params.retest_hard_reject_threshold,
                rejected=rejected,
                retest_matched_pairs=matched_pairs,
            ))

            if rejected:
                rejected_scenes.add(scene_id)

        result[user_id] = {
            "scene_details": [d.model_dump() for d in scene_details],
            "rejected_scenes": rejected_scenes,
        }

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 用户组一致性检验
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_scores(data: list[EvalRecord]) -> list[EvalRecord]:
    """评分归一化: score > 1.0 → 1.0"""
    for r in data:
        if r.score_a > 1.0:
            r.score_a = 1.0
        if r.score_b > 1.0:
            r.score_b = 1.0
    return data


def clean_user_group_consistency(
    data: list[EvalRecord],
    params: CleaningParams,
    scene_names: dict[int, str],
) -> dict:
    """
    用户组一致性检验 (逐场景) — log B-T 强度 + Pearson r。
    """
    groups: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in data:
        groups[(r.user_id, r.pair_id)].append(r)

    original_data = []
    for recs in groups.values():
        recs.sort(key=lambda r: r.eval_id)
        original_data.append(recs[0])

    original_data = _normalize_scores(original_data)

    all_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
    for r in original_data:
        all_by_scene[r.scene_id].append(r)

    user_scene_index: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in original_data:
        user_scene_index[(r.user_id, r.scene_id)].append(r)

    user_scenes = set(user_scene_index.keys())

    r_results: dict[tuple[int, int], float] = {}

    for (user_id, scene_id) in sorted(user_scenes):
        user_recs = user_scene_index[(user_id, scene_id)]
        user_bt = bradley_terry(user_recs, scene_id=scene_id)
        group_recs = [r for r in all_by_scene.get(scene_id, []) if r.user_id != user_id]
        group_bt = bradley_terry(group_recs, scene_id=scene_id)

        common = sorted(set(user_bt) & set(group_bt))
        if len(common) < params.min_devices_per_scene:
            r_results[(user_id, scene_id)] = 0.0
            continue

        x = [math.log(max(user_bt[m], 1e-12)) for m in common]
        y = [math.log(max(group_bt[m], 1e-12)) for m in common]
        r_val = pearson_correlation(x, y, params.min_devices_per_scene)
        r_results[(user_id, scene_id)] = r_val if r_val is not None else 0.0

    scene_r_list: dict[int, list[float]] = defaultdict(list)
    for (uid, sid), r_val in r_results.items():
        scene_r_list[sid].append(r_val)

    scene_thresholds: dict[int, float] = {}
    for sid, r_vals in scene_r_list.items():
        raw = _mean(r_vals) - _std(r_vals)
        scene_thresholds[sid] = min(raw, params.group_max_threshold)

    rejected_by_scene: dict[int, set[int]] = defaultdict(set)
    scene_stats = {}

    for (user_id, scene_id) in sorted(user_scenes):
        r_val = r_results[(user_id, scene_id)]
        dyn_threshold = scene_thresholds.get(scene_id, params.group_max_threshold)
        rejected = (r_val < dyn_threshold)

        if rejected:
            rejected_by_scene[scene_id].add(user_id)

    for scene_id in all_by_scene:
        total = len(set(r.user_id for r in all_by_scene[scene_id]))
        rejected_count = len(rejected_by_scene.get(scene_id, set()))
        scene_stats[scene_id] = {
            "scene_name": scene_names.get(scene_id, f"场景{scene_id}"),
            "total_user_scenes": total,
            "passed": total - rejected_count,
            "rejected": rejected_count,
        }

    return {
        "rejected_by_scene": rejected_by_scene,
        "scene_stats": scene_stats,
        "r_results": r_results,
        "scene_thresholds": scene_thresholds,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主清洗流程
# ═══════════════════════════════════════════════════════════════════════════════

def execute_cleaning(db: Session, params: CleaningParams) -> dict:
    """执行完整的数据清洗流程。"""
    records = load_eval_records(db)
    scene_names = get_scene_names(db)

    if not records:
        return {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "single_user_details": {},
            "user_group_details": {},
            "leaderboard_updated": False,
        }

    total_records = len(records)

    single_user_result = clean_single_user_consistency(records, params, scene_names)

    invalid_eval_ids = set()
    for user_id, user_result in single_user_result.items():
        for scene_id in user_result["rejected_scenes"]:
            for r in records:
                if r.user_id == user_id and r.scene_id == scene_id:
                    invalid_eval_ids.add(r.eval_id)

    valid_for_group = [r for r in records if r.eval_id not in invalid_eval_ids]
    group_result = clean_user_group_consistency(valid_for_group, params, scene_names)

    for scene_id, rejected_users in group_result["rejected_by_scene"].items():
        for r in valid_for_group:
            if r.user_id in rejected_users and r.scene_id == scene_id:
                invalid_eval_ids.add(r.eval_id)

    _update_evaluations(db, records, invalid_eval_ids, single_user_result, group_result, scene_names)

    valid_records = total_records - len(invalid_eval_ids)

    # 查询用户名称映射
    user_ids = {int(uid) for uid in single_user_result.keys()}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_name_map = {u.id: u.display_name or u.username for u in users}

    single_user_details = {}
    for user_id, user_result in single_user_result.items():
        uid = int(user_id)
        single_user_details[user_id] = {
            "user_name": user_name_map.get(uid, f"用户{uid}"),
            "scene_details": user_result["scene_details"]
        }

    user_group_details = {}
    for scene_id, stats in group_result["scene_stats"].items():
        user_group_details[str(scene_id)] = stats

    # 保存清洗元数据（时间戳、参数和结果）
    cleaning_time = datetime.now().isoformat()
    _save_cleaning_meta({
        "last_cleaned_at": cleaning_time,
        "params": {
            "retest_agreement_threshold": params.retest_agreement_threshold,
            "retest_hard_reject_threshold": params.retest_hard_reject_threshold,
            "group_max_threshold": params.group_max_threshold,
            "retest_ratio": params.retest_ratio,
            "min_devices_per_scene": params.min_devices_per_scene,
        },
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": len(invalid_eval_ids),
        "single_user_details": single_user_details,
        "user_group_details": user_group_details,
    })

    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": len(invalid_eval_ids),
        "single_user_details": single_user_details,
        "user_group_details": user_group_details,
        "leaderboard_updated": True,
    }


def _update_evaluations(
    db: Session,
    records: list[EvalRecord],
    invalid_eval_ids: set[int],
    single_user_result: dict,
    group_result: dict,
    scene_names: dict[int, str],
) -> None:
    """更新 evaluations 表的清洗结果"""
    user_scene_reject_info: dict[tuple[int, int], dict] = {}

    for user_id, user_result in single_user_result.items():
        if user_result.get("insufficient_retest"):
            retest_info = user_result.get("retest_info", {})
            for sid in user_result["rejected_scenes"]:
                user_scene_reject_info[(user_id, sid)] = {
                    "type": RejectType.INSUFFICIENT_RETEST.value,
                    "detail": {
                        "retest_count": retest_info.get("retest_count", 0),
                        "total_pairs": retest_info.get("total_pairs", 0),
                        "required_retest": retest_info.get("required_retest", 0),
                    },
                }
        else:
            for scene_detail in user_result["scene_details"]:
                if scene_detail.get("rejected"):
                    sid = scene_detail["scene_id"]
                    user_scene_reject_info[(user_id, sid)] = {
                        "type": RejectType.RETEST_RELIABILITY.value,
                        "detail": {
                            "scene_id": sid,
                            "scene_name": scene_names.get(sid, f"场景{sid}"),
                            "retest_agreement_score": scene_detail.get("retest_agreement_score", 0),
                            "retest_agreement_threshold": scene_detail.get("retest_agreement_threshold", 0),
                            "retest_hard_reject_threshold": scene_detail.get("retest_hard_reject_threshold", 0.55),
                            "retest_matched_pairs": scene_detail.get("retest_matched_pairs", 0),
                        },
                    }

    for scene_id, rejected_users in group_result["rejected_by_scene"].items():
        for user_id in rejected_users:
            if (user_id, scene_id) not in user_scene_reject_info:
                r_val = group_result.get("r_results", {}).get((user_id, scene_id), 0.0)
                dyn_threshold = group_result.get("scene_thresholds", {}).get(scene_id, 0.0)
                user_scene_reject_info[(user_id, scene_id)] = {
                    "type": RejectType.GROUP_CONSENSUS.value,
                    "detail": {
                        "scene_id": scene_id,
                        "scene_name": scene_names.get(scene_id, f"场景{scene_id}"),
                        "group_pearson_r": round(r_val, 4),
                        "group_dynamic_threshold": round(dyn_threshold, 4),
                    },
                }

    for r in records:
        is_valid = 0 if r.eval_id in invalid_eval_ids else 1
        reject_type = None
        reject_detail = None

        if not is_valid:
            info = user_scene_reject_info.get((r.user_id, r.scene_id))
            if info:
                reject_type = info["type"]
                reject_detail = info["detail"]

        db.query(Evaluation).filter(Evaluation.id == r.eval_id).update({
            "is_valid": is_valid,
            "reject_type": reject_type,
            "reject_detail": reject_detail,
        })

    db.commit()


def get_cleaning_status(db: Session) -> dict:
    """获取清洗状态"""
    cleaned = db.query(Evaluation).filter(Evaluation.is_valid.isnot(None)).first()
    has_cleaned = cleaned is not None

    # 从元数据文件获取清洗时间
    meta = _load_cleaning_meta()
    last_cleaned_at = meta.get("last_cleaned_at") if has_cleaned else None

    cleaned_record_count = 0
    if has_cleaned:
        cleaned_record_count = db.query(Evaluation).filter(Evaluation.is_valid.isnot(None)).count()

    # 统计各状态的评测数
    total_count = db.query(Evaluation).count()
    submitted_count = db.query(Evaluation).filter(Evaluation.status == "submitted").count()
    draft_count = db.query(Evaluation).filter(Evaluation.status == "draft").count()

    new_record_count = db.query(Evaluation).filter(
        Evaluation.status == "submitted",
        Evaluation.is_valid.is_(None),
    ).count()

    return {
        "has_cleaned": has_cleaned,
        "last_cleaned_at": last_cleaned_at,
        "cleaned_record_count": cleaned_record_count,
        "current_record_count": submitted_count,
        "new_record_count": new_record_count,
        "needs_refresh": new_record_count > 0,
        "debug_total_count": total_count,
        "debug_draft_count": draft_count,
    }


def export_cleaning_report(db: Session) -> str:
    """导出清洗报告为文本"""
    meta = _load_cleaning_meta()
    invalid_records = (
        db.query(Evaluation)
        .filter(Evaluation.is_valid == 0)
        .all()
    )

    params = meta.get("params", {})
    lines = [
        "=" * 60,
        "数据清洗报告",
        "=" * 60,
        "",
        f"清洗时间: {meta.get('last_cleaned_at', 'N/A')}",
        "",
        "清洗参数:",
        f"  重测一致性阈值: {params.get('retest_agreement_threshold', 'N/A')}",
        f"  重测硬拒绝阈值: {params.get('retest_hard_reject_threshold', 'N/A')}",
        f"  用户组最大阈值: {params.get('group_max_threshold', 'N/A')}",
        f"  复评比例要求: {params.get('retest_ratio', 'N/A')}",
        f"  最小设备数: {params.get('min_devices_per_scene', 'N/A')}",
        "",
        f"总评测数: {meta.get('total_records', 'N/A')}",
        f"有效评测数: {meta.get('valid_records', 'N/A')}",
        f"无效评测数: {meta.get('invalid_records', len(invalid_records))}",
        "",
    ]

    # 单用户一致性检验结果
    single_user = meta.get("single_user_details", {})
    if single_user:
        lines.extend([
            "-" * 60,
            "单用户一致性检验（重测信度）",
            "-" * 60,
            f"{'用户':<15}{'场景':<25}{'一致性得分':<12}{'阈值':<8}{'状态':<6}{'重测对数':<8}",
            "-" * 74,
        ])
        for user_id, data in single_user.items():
            user_name = data.get("user_name", f"用户{user_id}")
            for detail in data.get("scene_details", []):
                status = "✓" if not detail.get("rejected") else "✗"
                lines.append(
                    f"{user_name:<15}"
                    f"{detail.get('scene_name', ''):<25}"
                    f"{detail.get('retest_agreement_score', 0):<12.2f}"
                    f"{detail.get('retest_agreement_threshold', 0):<8.2f}"
                    f"{status:<6}"
                    f"{detail.get('retest_matched_pairs', 0):<8}"
                )
        lines.append("")

    # 用户组一致性检验结果
    user_group = meta.get("user_group_details", {})
    if user_group:
        lines.extend([
            "-" * 60,
            "用户组一致性检验",
            "-" * 60,
            f"{'场景':<30}{'参评用户数':<10}{'通过':<8}{'拒绝':<8}{'通过率':<8}",
            "-" * 64,
        ])
        for scene_id, stats in user_group.items():
            total = stats.get("total_user_scenes", 0)
            passed = stats.get("passed", 0)
            rate = f"{(passed / total * 100):.1f}%" if total > 0 else "-"
            lines.append(
                f"{stats.get('scene_name', ''):<30}"
                f"{total:<10}"
                f"{passed:<8}"
                f"{stats.get('rejected', 0):<8}"
                f"{rate:<8}"
            )
        lines.append("")

    # 无效记录详情
    lines.extend([
        "-" * 60,
        "无效记录详情",
        "-" * 60,
    ])
    for rec in invalid_records:
        lines.append(
            f"评测ID: {rec.id} | 用户ID: {rec.user_id} | "
            f"拒绝类型: {rec.reject_type or 'N/A'} | "
            f"详情: {rec.reject_detail or 'N/A'}"
        )

    lines.extend(["", "=" * 60, "报告结束"])
    return "\n".join(lines)
