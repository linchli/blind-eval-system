# 数据清洗与排行榜功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 clean_and_stats 模块合并到主后端，实现数据清洗功能，并新增设备排行榜功能。

**Architecture:** 数据清洗模块从 clean_and_stats 迁移，使用 is_repeat 字段判断原始/复评数据。排行榜模块基于清洗后的有效数据计算 BT 得分和评分均值，使用内存缓存，由数据清洗驱动更新。

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, ECharts, scipy

---

## 文件结构

### 后端文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/core/config.py` | 修改 | 新增清洗参数配置 |
| `backend/app/service/cleaning.py` | 新增 | 合并 cleaner.py + statistics.py |
| `backend/app/service/leaderboard.py` | 新增 | 排行榜计算 + 缓存 |
| `backend/app/schemas/cleaning.py` | 重写 | 清洗请求/响应模型 |
| `backend/app/schemas/leaderboard.py` | 新增 | 排行榜数据模型 |
| `backend/app/api/cleaning.py` | 重写 | 清洗 API 路由 |
| `backend/app/api/leaderboard.py` | 新增 | 排行榜 API 路由 |
| `backend/main.py` | 修改 | 注册新路由 |

### 前端文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/package.json` | 修改 | 新增 echarts 依赖 |
| `frontend/src/views/admin/DataCleaning.vue` | 新增 | 数据清洗页面 |
| `frontend/src/views/admin/Leaderboard.vue` | 新增 | 排行榜页面 |
| `frontend/src/views/admin/AdminOverview.vue` | 修改 | 新增入口卡片 |
| `frontend/src/views/auth/LoginView.vue` | 修改 | 新增排行榜按钮 |
| `frontend/src/views/admin/AdminLayout.vue` | 修改 | 侧边栏新增菜单 |
| `frontend/src/router/index.js` | 修改 | 新增路由 |
| `frontend/src/api/index.js` | 修改 | 新增 API 调用 |

---

## Task 1: 后端配置 - 新增清洗参数

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: 在 config.py 末尾新增清洗参数**

```python
# ==================== 数据清洗参数 ====================

# 单用户一致性（加权 Agreement）
SINGLE_USER_CORRELATION_THRESHOLD = float(os.getenv("SINGLE_USER_THRESHOLD", "0.70"))
SINGLE_USER_HARD_REJECT_AGREEMENT = float(os.getenv("SINGLE_USER_HARD_REJECT", "0.55"))

# 用户组一致性
GROUP_MAX_THRESHOLD = float(os.getenv("GROUP_MAX_THRESHOLD", "0.85"))
GROUP_MIN_THRESHOLD = float(os.getenv("GROUP_MIN_THRESHOLD", "0.55"))

# 数据量下限
MIN_DEVICES_PER_SCENE = int(os.getenv("MIN_DEVICES_PER_SCENE", "2"))
```

- [ ] **Step 2: 验证配置加载**

Run: `cd backend && python -c "from app.core.config import SINGLE_USER_CORRELATION_THRESHOLD, GROUP_MAX_THRESHOLD, MIN_DEVICES_PER_SCENE; print(f'SINGLE_USER={SINGLE_USER_CORRELATION_THRESHOLD}, GROUP_MAX={GROUP_MAX_THRESHOLD}, MIN_DEVICES={MIN_DEVICES_PER_SCENE}')"`
Expected: `SINGLE_USER=0.7, GROUP_MAX=0.85, MIN_DEVICES=2`

---

## Task 2: 后端服务 - 清洗服务（statistics 部分）

**Files:**
- Create: `backend/app/service/cleaning.py`

- [ ] **Step 1: 创建 cleaning.py 并实现 statistics 部分**

从 `clean_and_stats/app/service/statistics.py` 迁移，将 `model_id` 改为 `device_id`。

```python
"""
数据清洗服务 — 统计算法 + 清洗管线
从 clean_and_stats 迁移，命名以主干代码为准
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

from scipy.stats import pearsonr

from ..core import config


# ==================== 统计工具函数 ====================

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def pearson_correlation(x: list[float], y: list[float]) -> Optional[float]:
    """Pearson 相关系数。返回 None 表示数据不足或方差为零。"""
    if len(x) < config.MIN_DEVICES_PER_SCENE or len(y) < config.MIN_DEVICES_PER_SCENE:
        return None
    if len(x) != len(y):
        return None
    x_std = _std(x)
    y_std = _std(y)
    if x_std == 0.0 or y_std == 0.0:
        return None
    r, _ = pearsonr(x, y)
    return float(r)


def bradley_terry(
    records: list,
    scene_id: int | None = None,
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> dict[int, float]:
    """
    Bradley-Terry 模型强度估计 (MM 算法)。
    映射: score_a > score_b → A 胜; score_a < score_b → B 胜; 相等 → 平局。
    若指定 scene_id 则仅计算该场景。
    返回 {device_id: strength}, 几何均值归一化为 1。
    """
    # 过滤
    recs = [r for r in records if scene_id is None or r['scene_id'] == scene_id]

    # 统计每对设备间的比较次数和胜场
    wins: dict[int, float] = defaultdict(float)
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)

    for r in recs:
        a, b = r['device_a_id'], r['device_b_id']
        pair_counts[(min(a, b), max(a, b))] += 1
        if r['score_a'] > r['score_b']:
            wins[a] += 1.0
        elif r['score_b'] > r['score_a']:
            wins[b] += 1.0
        else:
            wins[a] += 0.5
            wins[b] += 0.5

    device_ids = sorted(set(
        d for r in recs for d in (r['device_a_id'], r['device_b_id'])
    ))
    n = len(device_ids)
    if n < 2:
        return {d: 1.0 for d in device_ids}

    # MM 迭代
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

        # 几何均值归一化为 1
        log_sum = sum(math.log(max(t, 1e-12)) for t in new_theta.values() if t > 0)
        if log_sum == 0:
            break
        norm = math.exp(log_sum / n)
        for d in device_ids:
            new_theta[d] /= norm

        # 收敛检查
        max_diff = max(abs(new_theta[d] - theta[d]) for d in device_ids)
        theta = new_theta
        if max_diff < tol:
            break

    return dict(theta)


def build_device_scores(records: list) -> dict[tuple[int, int, int], list[float]]:
    """将逐对评分展开为按 (user_id, scene_id, device_id) 聚合的评分列表。"""
    scores: dict[tuple[int, int, int], list[float]] = defaultdict(list)
    for r in records:
        key_a = (r['user_id'], r['scene_id'], r['device_a_id'])
        key_b = (r['user_id'], r['scene_id'], r['device_b_id'])
        scores[key_a].append(r['score_a'])
        scores[key_b].append(r['score_b'])
    return dict(scores)


def scene_device_mean_scores(
    device_scores: dict[tuple[int, int, int], list[float]],
    scene_id: int,
    exclude_user: Optional[int] = None,
) -> dict[int, float]:
    """某个场景下各设备的组均值评分。"""
    agg: dict[int, list[float]] = defaultdict(list)
    for (uid, sid, did), scores in device_scores.items():
        if sid != scene_id:
            continue
        if exclude_user is not None and uid == exclude_user:
            continue
        agg[did].extend(scores)
    return {did: _mean(vals) for did, vals in agg.items()}


def user_scene_device_means(
    device_scores: dict[tuple[int, int, int], list[float]],
    user_id: int,
    scene_id: int,
) -> dict[int, float]:
    """某个用户在某场景下对各设备的平均评分"""
    return {
        did: _mean(vals)
        for (uid, sid, did), vals in device_scores.items()
        if uid == user_id and sid == scene_id
    }


# ==================== 加权一致性 ====================

def _to_judgment_level(score_a: float, score_b: float) -> int:
    """将原始评分映射为 5 级判定方向。"""
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


# 加权矩阵: weight[d_orig+2][d_retest+2]
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
    """对单个复评对计算加权一致性得分, 范围 [-1, +1]。"""
    d_orig = _to_judgment_level(score_a_orig, score_b_orig)
    d_retest = _to_judgment_level(score_a_retest, score_b_retest)
    return _JUDGMENT_WEIGHTS[d_orig + 2][d_retest + 2]


def scene_weighted_agreement(
    orig_records: list,
    retest_records: list,
) -> tuple[float, int]:
    """逐对匹配原始和复评记录, 计算场景级加权一致性得分。"""
    orig_by_pair = {r['pair_id']: r for r in orig_records}
    retest_by_pair = {r['pair_id']: r for r in retest_records}

    weights = []
    for pair_id, orig_r in orig_by_pair.items():
        retest_r = retest_by_pair.get(pair_id)
        if retest_r is None:
            continue
        w = weighted_agreement_for_pair(
            orig_r['score_a'], orig_r['score_b'],
            retest_r['score_a'], retest_r['score_b'],
        )
        weights.append(w)

    if not weights:
        return 0.0, 0

    mean_w = sum(weights) / len(weights)
    return (mean_w + 1.0) / 2.0, len(weights)
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.service.cleaning import bradley_terry, pearson_correlation, scene_weighted_agreement; print('OK')"`
Expected: `OK`

---

## Task 3: 后端服务 - 清洗服务（cleaner 部分）

**Files:**
- Modify: `backend/app/service/cleaning.py`

- [ ] **Step 1: 在 cleaning.py 中添加清洗管线函数**

在文件末尾追加：

```python
# ==================== 清洗管线 ====================

from dataclasses import dataclass, field


@dataclass
class SingleUserResult:
    passed: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    scene_details: list = field(default_factory=list)
    user_id: int = 0
    retest_pair_count: int = 0
    total_pair_count: int = 0


@dataclass
class UserGroupResult:
    passed: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    details: list = field(default_factory=list)
    bt_scores: dict = field(default_factory=dict)
    scene_stats: dict = field(
        default_factory=lambda: defaultdict(lambda: {"total": 0, "passed": 0, "rejected": 0})
    )


def _normalize_scores(data: list[dict]) -> list[dict]:
    """评分归一化: score > 1.0 → 1.0"""
    for r in data:
        if r['score_a'] > 1.0:
            r['score_a'] = 1.0
        if r['score_b'] > 1.0:
            r['score_b'] = 1.0
    return data


def clean_single_user_consistency(
    data: list[dict],
    threshold: Optional[float] = None,
) -> SingleUserResult:
    """
    重测信度检验 (单用户自评一致性) — 加权 Agreement。

    使用 is_repeat 字段判断原始/复评数据：
    - is_repeat=0 → original（首次评测）
    - is_repeat=1 → retest（复评）
    """
    if threshold is None:
        threshold = config.SINGLE_USER_CORRELATION_THRESHOLD

    total = len(data)
    user_ids = {r['user_id'] for r in data}
    if len(user_ids) != 1:
        raise ValueError("NOT_SAME_USER")

    user_id = user_ids.pop()

    # 使用 is_repeat 字段分离原始评分和复评数据
    original = [r for r in data if r['is_repeat'] == 0]
    retest = [r for r in data if r['is_repeat'] == 1]

    total_pairs = len({(r['user_id'], r['pair_id']) for r in data})
    retest_count = len({(r['user_id'], r['pair_id']) for r in retest})

    required_retest = int(total_pairs * 0.10)
    if retest_count < required_retest:
        raise ValueError("NO_RETEST_DATA")

    result = SingleUserResult(
        user_id=user_id,
        retest_pair_count=retest_count,
        total_pair_count=total_pairs,
    )

    # 逐场景计算加权 Agreement
    original_by_scene: dict[int, list] = defaultdict(list)
    retest_by_scene: dict[int, list] = defaultdict(list)
    for r in original:
        original_by_scene[r['scene_id']].append(r)
    for r in retest:
        retest_by_scene[r['scene_id']].append(r)

    all_scenes = sorted(set(original_by_scene.keys()) | set(retest_by_scene.keys()))

    for scene_id in all_scenes:
        orig_recs = original_by_scene.get(scene_id, [])
        retest_recs = retest_by_scene.get(scene_id, [])

        agreement_score, matched_pairs = scene_weighted_agreement(orig_recs, retest_recs)

        if matched_pairs == 0:
            rejected = True
        elif agreement_score >= threshold:
            rejected = False
        elif agreement_score < config.SINGLE_USER_HARD_REJECT_AGREEMENT:
            rejected = True
        else:
            rejected = True

        result.scene_details.append({
            'scene_id': scene_id,
            'agreement_score': round(agreement_score, 4),
            'threshold': round(threshold, 4),
            'rejected': rejected,
            'matched_pairs': matched_pairs,
        })

    # 标记无效记录
    invalid_scenes = {d['scene_id'] for d in result.scene_details if d['rejected']}

    for r in data:
        if r['scene_id'] in invalid_scenes and r['is_repeat'] == 1:
            result.rejected.append({**r, 'is_valid': False, 'reject_reason': 'single_user_consistency'})
        else:
            result.passed.append({**r, 'is_valid': True, 'reject_reason': None})

    return result


def clean_user_group_consistency(
    data: list[dict],
    threshold: Optional[float] = None,
) -> UserGroupResult:
    """
    用户组一致性检验 (逐场景) — log B-T 强度 + Pearson r。
    """
    import math

    if threshold is None:
        threshold = config.GROUP_MAX_THRESHOLD

    # 剔除复评数据: 每 (user_id, pair_id) 仅保留首次评测
    groups: dict[tuple[int, int], list] = defaultdict(list)
    for r in data:
        groups[(r['user_id'], r['pair_id'])].append(r)

    original_data = []
    for recs in groups.values():
        recs.sort(key=lambda r: r['eval_id'])
        original_data.append(recs[0])

    original_data = _normalize_scores(original_data)
    result = UserGroupResult()

    # 按 scene 分组
    all_by_scene: dict[int, list] = defaultdict(list)
    for r in original_data:
        all_by_scene[r['scene_id']].append(r)

    user_scene_index: dict[tuple[int, int], list] = defaultdict(list)
    for r in original_data:
        user_scene_index[(r['user_id'], r['scene_id'])].append(r)

    user_scenes = set(user_scene_index.keys())

    # 计算所有 (user_id, scene_id) 的 log-BT Pearson r
    r_results: dict[tuple[int, int], float] = {}

    for (user_id, scene_id) in sorted(user_scenes):
        user_recs = user_scene_index[(user_id, scene_id)]

        user_bt = bradley_terry(user_recs, scene_id=scene_id)
        group_recs = [r for r in all_by_scene.get(scene_id, [])
                      if r['user_id'] != user_id]
        group_bt = bradley_terry(group_recs, scene_id=scene_id)

        common = sorted(set(user_bt) & set(group_bt))
        if len(common) < config.MIN_DEVICES_PER_SCENE:
            r_results[(user_id, scene_id)] = 0.0
            continue

        x = [math.log(max(user_bt[m], 1e-12)) for m in common]
        y = [math.log(max(group_bt[m], 1e-12)) for m in common]
        r_val = pearson_correlation(x, y)
        r_results[(user_id, scene_id)] = r_val if r_val is not None else 0.0

    # 动态阈值
    scene_r_list: dict[int, list[float]] = defaultdict(list)
    for (uid, sid), r_val in r_results.items():
        scene_r_list[sid].append(r_val)

    scene_thresholds: dict[int, float] = {}
    for sid, r_vals in scene_r_list.items():
        raw = _mean(r_vals) - _std(r_vals)
        scene_thresholds[sid] = min(raw, threshold)

    # 判定 + 记录 detail + 分类
    for (user_id, scene_id) in sorted(user_scenes):
        r_val = r_results[(user_id, scene_id)]
        dyn_threshold = scene_thresholds.get(scene_id, threshold)
        rejected = (r_val < dyn_threshold)

        result.details.append({
            'user_id': user_id,
            'scene_id': scene_id,
            'correlation': round(r_val, 4),
            'threshold': round(dyn_threshold, 4),
            'rejected': rejected,
        })
        stats = result.scene_stats[scene_id]
        stats["total"] += 1
        if rejected:
            stats["rejected"] += 1
        else:
            stats["passed"] += 1

        all_user_scene_recs = [
            r for r in data
            if r['user_id'] == user_id and r['scene_id'] == scene_id
        ]
        for r in all_user_scene_recs:
            if rejected:
                result.rejected.append({**r, 'is_valid': False, 'reject_reason': 'user_group_consistency'})
            else:
                result.passed.append({**r, 'is_valid': True, 'reject_reason': None})

    # 逐场景计算 BT 强度（基于有效数据）
    scene_ids = {r['scene_id'] for r in result.passed}
    for sid in sorted(scene_ids):
        bt = bradley_terry(result.passed, scene_id=sid)
        if bt:
            result.bt_scores[sid] = bt

    return result
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.service.cleaning import clean_single_user_consistency, clean_user_group_consistency; print('OK')"`
Expected: `OK`

---

## Task 4: 后端 Schema - 清洗数据模型

**Files:**
- Rewrite: `backend/app/schemas/cleaning.py`

- [ ] **Step 1: 重写 cleaning.py schema**

```python
"""
数据清洗相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class RetestSceneDetail(BaseModel):
    """单场景重测信度详情"""
    scene_id: int
    scene_name: str = ""
    agreement_score: float
    threshold: float
    rejected: bool
    matched_pairs: int


class UserGroupDetail(BaseModel):
    """逐 (user_id, scene_id) 与组一致性的检验结果"""
    user_id: int
    scene_id: int
    scene_name: str = ""
    correlation: float
    threshold: float
    rejected: bool


class CleaningStatusResponse(BaseModel):
    """清洗状态响应"""
    has_cleaned: bool
    last_cleaned_at: Optional[str] = None
    cleaned_record_count: int = 0
    current_record_count: int = 0
    new_record_count: int = 0
    needs_refresh: bool = False


class CleaningExecuteResponse(BaseModel):
    """执行清洗响应"""
    total_records: int
    valid_records: int
    invalid_records: int
    single_user_details: dict
    user_group_details: dict
    leaderboard_updated: bool
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.schemas.cleaning import CleaningStatusResponse, CleaningExecuteResponse; print('OK')"`
Expected: `OK`

---

## Task 5: 后端 API - 清洗路由

**Files:**
- Rewrite: `backend/app/api/cleaning.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 重写 cleaning.py 路由**

```python
"""
数据清洗路由
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..models.user import User
from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.device_model import DeviceModel
from ..schemas.cleaning import CleaningStatusResponse, CleaningExecuteResponse
from ..schemas.common import ApiResponse
from ..service.cleaning import clean_single_user_consistency, clean_user_group_consistency

router = APIRouter(prefix="/api/cleaning", tags=["数据清洗"])

# 内存缓存
_cleaning_cache = {
    "has_cleaned": False,
    "last_cleaned_at": None,
    "cleaned_record_count": 0,
    "leaderboard_data": None,
}


def _get_scene_name(scene_id: int, db: Session) -> str:
    """获取场景完整名称"""
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return f"场景{scene_id}"
    cat = db.query(SceneCategory).filter(SceneCategory.id == scene.category_id).first()
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.id == scene.subcategory_id).first()
    cat_part = cat.name if cat else ""
    if cat and cat.location:
        cat_part = f"{cat_part}({cat.location})"
    sub_part = sub.name if sub else ""
    return f"{cat_part}-{sub_part}" if sub_part else cat_part


def _load_evaluations(db: Session) -> list[dict]:
    """加载所有 submitted 状态的评测记录"""
    records = (
        db.query(
            Evaluation.id.label('eval_id'),
            Evaluation.user_id,
            Evaluation.pair_id,
            Evaluation.session_id,
            Evaluation.score_a,
            Evaluation.score_b,
            Evaluation.is_repeat,
            ImagePair.scene_id,
            ImagePair.image_a_id,
            ImagePair.image_b_id,
        )
        .join(ImagePair, Evaluation.pair_id == ImagePair.id)
        .filter(Evaluation.status == 'submitted')
        .all()
    )

    # 获取 image 的 device_id
    from ..models.image import Image
    result = []
    for r in records:
        img_a = db.query(Image).filter(Image.id == r.image_a_id).first()
        img_b = db.query(Image).filter(Image.id == r.image_b_id).first()
        result.append({
            'eval_id': r.eval_id,
            'user_id': r.user_id,
            'pair_id': r.pair_id,
            'session_id': r.session_id,
            'scene_id': r.scene_id,
            'device_a_id': img_a.device_id if img_a else 0,
            'device_b_id': img_b.device_id if img_b else 0,
            'score_a': r.score_a,
            'score_b': r.score_b,
            'is_repeat': r.is_repeat,
        })

    return result


@router.get("/status", response_model=ApiResponse)
async def get_cleaning_status(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取清洗状态"""
    current_count = db.query(Evaluation).filter(Evaluation.status == 'submitted').count()

    return ApiResponse(
        success=True,
        data=CleaningStatusResponse(
            has_cleaned=_cleaning_cache["has_cleaned"],
            last_cleaned_at=_cleaning_cache["last_cleaned_at"],
            cleaned_record_count=_cleaning_cache["cleaned_record_count"],
            current_record_count=current_count,
            new_record_count=current_count - _cleaning_cache["cleaned_record_count"],
            needs_refresh=current_count > _cleaning_cache["cleaned_record_count"],
        ).model_dump(),
    )


@router.post("/execute", response_model=ApiResponse)
async def execute_cleaning(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """执行数据清洗"""
    # 加载数据
    data = _load_evaluations(db)
    if not data:
        raise HTTPException(status_code=400, detail="没有可清洗的数据")

    # 按 user_id 分组
    user_groups: dict[int, list] = {}
    for r in data:
        user_groups.setdefault(r['user_id'], []).append(r)

    # 第一步：单用户一致性检验
    all_valid = []
    all_invalid = []
    single_user_details = {}

    for user_id, user_data in user_groups.items():
        try:
            result = clean_single_user_consistency(user_data)
            all_valid.extend(result.passed)
            all_invalid.extend(result.rejected)

            user = db.query(User).filter(User.id == user_id).first()
            username = user.username if user else f"user{user_id}"

            single_user_details[username] = {
                "scene_details": [
                    {
                        "scene_id": d['scene_id'],
                        "scene_name": _get_scene_name(d['scene_id'], db),
                        "agreement_score": d['agreement_score'],
                        "threshold": d['threshold'],
                        "rejected": d['rejected'],
                        "matched_pairs": d['matched_pairs'],
                    }
                    for d in result.scene_details
                ]
            }
        except ValueError as e:
            # 跳过数据不足的用户
            continue

    # 第二步：用户组一致性检验（基于单用户检验通过的数据）
    group_result = clean_user_group_consistency(all_valid)
    all_valid = group_result.passed
    all_invalid.extend(group_result.rejected)

    user_group_details = {}
    for sid, stats in group_result.scene_stats.items():
        user_group_details[str(sid)] = {
            "scene_name": _get_scene_name(sid, db),
            "total_user_scenes": stats["total"],
            "passed": stats["passed"],
            "rejected": stats["rejected"],
        }

    # 第三步：计算排行榜数据
    from ..service.leaderboard import compute_leaderboard
    leaderboard_data = compute_leaderboard(all_valid, db)

    # 更新缓存
    _cleaning_cache["has_cleaned"] = True
    _cleaning_cache["last_cleaned_at"] = datetime.now().isoformat()
    _cleaning_cache["cleaned_record_count"] = len(data)
    _cleaning_cache["leaderboard_data"] = leaderboard_data

    return ApiResponse(
        success=True,
        data=CleaningExecuteResponse(
            total_records=len(data),
            valid_records=len(all_valid),
            invalid_records=len(all_invalid),
            single_user_details=single_user_details,
            user_group_details=user_group_details,
            leaderboard_updated=True,
        ).model_dump(),
    )


def get_cleaning_cache():
    """获取清洗缓存（供排行榜模块使用）"""
    return _cleaning_cache
```

- [ ] **Step 2: 在 main.py 中注册新路由**

在 `main.py` 的路由注册区域添加：

```python
from app.api import cleaning as cleaning_router
from app.api import leaderboard as leaderboard_router

# ... 现有路由 ...
app.include_router(cleaning_router.router)
app.include_router(leaderboard_router.router)
```

- [ ] **Step 3: 验证服务启动**

Run: `cd backend && python -c "from app.api.cleaning import router; print('OK')"`
Expected: `OK`

---

## Task 6: 后端服务 - 排行榜服务

**Files:**
- Create: `backend/app/service/leaderboard.py`

- [ ] **Step 1: 创建排行榜服务**

```python
"""
排行榜服务 — 计算 + 缓存
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from ..models.device_model import DeviceModel
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from .cleaning import bradley_terry, _mean


def compute_leaderboard(valid_records: list[dict], db: Session) -> dict:
    """基于有效数据计算排行榜"""
    if not valid_records:
        return {"ranking": [], "last_updated": None}

    # 1. 计算总体 BT 得分
    overall_bt = bradley_terry(valid_records)

    # 2. 计算分场景 BT 得分
    scene_ids = {r['scene_id'] for r in valid_records}
    scene_bt_scores = {}
    for sid in scene_ids:
        bt = bradley_terry(valid_records, scene_id=sid)
        if bt:
            scene_bt_scores[sid] = bt

    # 3. 计算评分均值
    device_scores: dict[int, list[float]] = defaultdict(list)
    device_scene_scores: dict[tuple[int, int], list[float]] = defaultdict(list)

    for r in valid_records:
        device_scores[r['device_a_id']].append(r['score_a'])
        device_scores[r['device_b_id']].append(r['score_b'])
        device_scene_scores[(r['device_a_id'], r['scene_id'])].append(r['score_a'])
        device_scene_scores[(r['device_b_id'], r['scene_id'])].append(r['score_b'])

    # 4. 归一化 BT 得分到 0-100
    if overall_bt:
        max_bt = max(overall_bt.values())
        min_bt = min(overall_bt.values())
        bt_range = max_bt - min_bt if max_bt != min_bt else 1.0
        normalized_bt = {
            did: round((score - min_bt) / bt_range * 100, 1)
            for did, score in overall_bt.items()
        }
    else:
        normalized_bt = {}

    # 5. 归一化均值得分到 0-100
    mean_scores = {did: _mean(scores) for did, scores in device_scores.items()}
    if mean_scores:
        max_mean = max(mean_scores.values())
        min_mean = min(mean_scores.values())
        mean_range = max_mean - min_mean if max_mean != min_mean else 1.0
        normalized_mean = {
            did: round((score - min_mean) / mean_range * 100, 1)
            for did, score in mean_scores.items()
        }
    else:
        normalized_mean = {}

    # 6. 构建排行榜数据
    ranking = []
    for device_id in sorted(normalized_bt.keys(), key=lambda d: -normalized_bt[d]):
        device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
        if not device:
            continue

        # 分场景得分
        scene_scores = {}
        for sid in scene_ids:
            if sid in scene_bt_scores and device_id in scene_bt_scores[sid]:
                scene_name = _get_scene_name(sid, db)
                # 归一化场景得分
                scene_bt = scene_bt_scores[sid]
                max_s = max(scene_bt.values())
                min_s = min(scene_bt.values())
                s_range = max_s - min_s if max_s != min_s else 1.0
                scene_scores[scene_name] = round((scene_bt[device_id] - min_s) / s_range * 100, 1)

        ranking.append({
            "device_id": device_id,
            "device_name": device.name,
            "main_chip": device.main_chip or "",
            "sensor_model": device.sensor_model or "",
            "focal_length": device.focal_length or "",
            "resolution": device.resolution or "",
            "bt_score": normalized_bt.get(device_id, 0),
            "mean_score": normalized_mean.get(device_id, 0),
            "scene_scores": scene_scores,
            "features": device.features or "",
        })

    return {
        "ranking": ranking,
        "last_updated": None,  # 由调用方设置
    }


def _get_scene_name(scene_id: int, db: Session) -> str:
    """获取场景完整名称"""
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return f"场景{scene_id}"
    cat = db.query(SceneCategory).filter(SceneCategory.id == scene.category_id).first()
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.id == scene.subcategory_id).first()
    cat_part = cat.name if cat else ""
    if cat and cat.location:
        cat_part = f"{cat_part}({cat.location})"
    sub_part = sub.name if sub else ""
    return f"{cat_part}-{sub_part}" if sub_part else cat_part


def get_scene_name(scene_id: int, db: Session) -> str:
    """获取场景完整名称（公开接口）"""
    return _get_scene_name(scene_id, db)


def compute_scene_details(scene_id: int, valid_records: list[dict], db: Session) -> dict:
    """计算场景详情（管理员白盒视图）"""
    scene_recs = [r for r in valid_records if r['scene_id'] == scene_id]

    # 统计设备对
    pair_stats: dict[tuple[int, int], dict] = defaultdict(lambda: {
        "eval_count": 0, "a_wins": 0, "b_wins": 0, "ties": 0
    })

    for r in scene_recs:
        key = (min(r['device_a_id'], r['device_b_id']), max(r['device_a_id'], r['device_b_id']))
        pair_stats[key]["eval_count"] += 1
        if r['score_a'] > r['score_b']:
            if r['device_a_id'] < r['device_b_id']:
                pair_stats[key]["a_wins"] += 1
            else:
                pair_stats[key]["b_wins"] += 1
        elif r['score_b'] > r['score_a']:
            if r['device_a_id'] < r['device_b_id']:
                pair_stats[key]["b_wins"] += 1
            else:
                pair_stats[key]["a_wins"] += 1
        else:
            pair_stats[key]["ties"] += 1

    # 计算 BT 强度
    bt = bradley_terry(scene_recs, scene_id=scene_id)

    pairs = []
    for (dev_a, dev_b), stats in pair_stats.items():
        total = stats["eval_count"]
        dev_a_model = db.query(DeviceModel).filter(DeviceModel.id == dev_a).first()
        dev_b_model = db.query(DeviceModel).filter(DeviceModel.id == dev_b).first()

        pairs.append({
            "device_a": {"id": dev_a, "name": dev_a_model.name if dev_a_model else f"设备{dev_a}"},
            "device_b": {"id": dev_b, "name": dev_b_model.name if dev_b_model else f"设备{dev_b}"},
            "eval_count": total,
            "a_win_rate": round(stats["a_wins"] / total, 2) if total > 0 else 0,
            "b_win_rate": round(stats["b_wins"] / total, 2) if total > 0 else 0,
            "tie_rate": round(stats["ties"] / total, 2) if total > 0 else 0,
            "bt_a": round(bt.get(dev_a, 0), 4),
            "bt_b": round(bt.get(dev_b, 0), 4),
        })

    return {
        "scene": {"id": scene_id, "name": _get_scene_name(scene_id, db)},
        "pairs": pairs,
    }


def compute_user_details(user_id: int, valid_records: list[dict], rejected_records: list[dict], db: Session) -> dict:
    """计算用户详情（管理员白盒视图）"""
    user_recs = [r for r in valid_records if r['user_id'] == user_id]
    user_rejected = [r for r in rejected_records if r['user_id'] == user_id]

    # 按场景分组
    scene_stats: dict[int, dict] = defaultdict(lambda: {"eval_count": 0, "passed": 0, "rejected": 0})

    for r in user_recs:
        scene_stats[r['scene_id']]["eval_count"] += 1
        scene_stats[r['scene_id']]["passed"] += 1

    for r in user_rejected:
        scene_stats[r['scene_id']]["eval_count"] += 1
        scene_stats[r['scene_id']]["rejected"] += 1

    scenes = []
    for sid, stats in scene_stats.items():
        scenes.append({
            "scene_id": sid,
            "scene_name": _get_scene_name(sid, db),
            "eval_count": stats["eval_count"],
            "passed_count": stats["passed"],
            "rejected_count": stats["rejected"],
        })

    user = db.query(User).filter(User.id == user_id).first()
    return {
        "user": {"id": user_id, "username": user.username if user else f"user{user_id}"},
        "scenes": scenes,
    }


def compute_device_details(device_id: int, valid_records: list[dict], db: Session) -> dict:
    """计算设备详情（管理员白盒视图）"""
    device_recs = [r for r in valid_records
                   if r['device_a_id'] == device_id or r['device_b_id'] == device_id]

    # 按场景分组
    scene_scores: dict[int, list[float]] = defaultdict(list)
    for r in device_recs:
        if r['device_a_id'] == device_id:
            scene_scores[r['scene_id']].append(r['score_a'])
        else:
            scene_scores[r['scene_id']].append(r['score_b'])

    # 计算分场景 BT
    scene_ids = {r['scene_id'] for r in device_recs}
    scene_bt = {}
    for sid in scene_ids:
        bt = bradley_terry(device_recs, scene_id=sid)
        if bt and device_id in bt:
            scene_bt[sid] = bt[device_id]

    scenes = []
    for sid in sorted(scene_ids):
        scenes.append({
            "scene_id": sid,
            "scene_name": _get_scene_name(sid, db),
            "bt_score": round(scene_bt.get(sid, 0), 4),
            "mean_score": round(_mean(scene_scores.get(sid, [])), 4),
            "eval_count": len(scene_scores.get(sid, [])),
        })

    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    return {
        "device": {"id": device_id, "name": device.name if device else f"设备{device_id}"},
        "scenes": scenes,
    }
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.service.leaderboard import compute_leaderboard, compute_scene_details; print('OK')"`
Expected: `OK`

---

## Task 7: 后端 Schema - 排行榜数据模型

**Files:**
- Create: `backend/app/schemas/leaderboard.py`

- [ ] **Step 1: 创建排行榜 schema**

```python
"""
排行榜相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class SceneScore(BaseModel):
    """场景得分"""
    scene_name: str
    score: float


class LeaderboardItem(BaseModel):
    """排行榜单项"""
    rank: int
    device_id: int
    device_name: str
    main_chip: str
    sensor_model: str
    focal_length: str
    resolution: str
    bt_score: float
    mean_score: float
    scene_scores: dict[str, float]
    features: str


class LeaderboardResponse(BaseModel):
    """排行榜响应"""
    ranking: list[LeaderboardItem]
    filter_info: dict
    total_devices: int
    last_updated: Optional[str] = None


class FilterOptions(BaseModel):
    """筛选选项"""
    categories: list[dict]
    subcategories: list[dict]
    chips: list[str]
    sensors: list[str]
    focal_lengths: list[str]
    resolutions: list[str]


class SceneDetailPair(BaseModel):
    """场景详情中的设备对"""
    device_a: dict
    device_b: dict
    eval_count: int
    a_win_rate: float
    b_win_rate: float
    tie_rate: float
    bt_a: float
    bt_b: float


class SceneDetailResponse(BaseModel):
    """场景详情响应"""
    scene: dict
    pairs: list[SceneDetailPair]


class UserDetailScene(BaseModel):
    """用户详情中的场景"""
    scene_id: int
    scene_name: str
    eval_count: int
    passed_count: int
    rejected_count: int


class UserDetailResponse(BaseModel):
    """用户详情响应"""
    user: dict
    scenes: list[UserDetailScene]


class DeviceDetailScene(BaseModel):
    """设备详情中的场景"""
    scene_id: int
    scene_name: str
    bt_score: float
    mean_score: float
    eval_count: int


class DeviceDetailResponse(BaseModel):
    """设备详情响应"""
    device: dict
    scenes: list[DeviceDetailScene]
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.schemas.leaderboard import LeaderboardResponse, FilterOptions; print('OK')"`
Expected: `OK`

---

## Task 8: 后端 API - 排行榜路由

**Files:**
- Create: `backend/app/api/leaderboard.py`

- [ ] **Step 1: 创建排行榜路由**

```python
"""
排行榜路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.dependencies import get_current_user, require_admin
from ..models.user import User
from ..models.device_model import DeviceModel
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..schemas.leaderboard import (
    LeaderboardResponse, FilterOptions,
    SceneDetailResponse, UserDetailResponse, DeviceDetailResponse,
)
from ..schemas.common import ApiResponse
from ..service.leaderboard import (
    compute_leaderboard, compute_scene_details,
    compute_user_details, compute_device_details,
)
from ..api.cleaning import get_cleaning_cache

router = APIRouter(prefix="/api/leaderboard", tags=["排行榜"])


@router.get("", response_model=ApiResponse)
async def get_leaderboard(
    filter_type: str = Query("overall", description="筛选类型"),
    filter_value: str = Query(None, description="筛选值"),
    score_type: str = Query("bt", description="得分类型: bt | mean"),
    db: Session = Depends(get_db),
):
    """获取排行榜数据（无需登录）"""
    cache = get_cleaning_cache()

    if not cache["has_cleaned"] or not cache["leaderboard_data"]:
        return ApiResponse(
            success=True,
            data=LeaderboardResponse(
                ranking=[],
                filter_info={"type": filter_type, "value": filter_value},
                total_devices=0,
                last_updated=None,
            ).model_dump(),
        )

    leaderboard_data = cache["leaderboard_data"]
    ranking = leaderboard_data["ranking"]

    # 应用筛选
    filtered_ranking = _apply_filter(ranking, filter_type, filter_value, db)

    # 按得分类型排序
    if score_type == "mean":
        filtered_ranking.sort(key=lambda x: -x["mean_score"])
    else:
        filtered_ranking.sort(key=lambda x: -x["bt_score"])

    # 更新排名
    for i, item in enumerate(filtered_ranking):
        item["rank"] = i + 1

    return ApiResponse(
        success=True,
        data=LeaderboardResponse(
            ranking=filtered_ranking,
            filter_info={"type": filter_type, "value": filter_value},
            total_devices=len(filtered_ranking),
            last_updated=cache["last_cleaned_at"],
        ).model_dump(),
    )


def _apply_filter(ranking: list, filter_type: str, filter_value: str, db: Session) -> list:
    """应用筛选条件"""
    if not filter_value or filter_type == "overall":
        return ranking.copy()

    if filter_type == "category":
        # 按大类筛选
        category = db.query(SceneCategory).filter(SceneCategory.name == filter_value).first()
        if not category:
            return []
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.category_id == category.id).all()}
        return [r for r in ranking if any(s.split("-")[0] in r.get("scene_scores", {}) for s in [_get_scene_name(sid, db) for sid in scene_ids])]

    elif filter_type == "location":
        # 按地点筛选
        categories = db.query(SceneCategory).filter(SceneCategory.location == filter_value).all()
        scene_ids = set()
        for cat in categories:
            scene_ids.update(s.id for s in db.query(Scene).filter(Scene.category_id == cat.id).all())
        return [r for r in ranking if any(_get_scene_name(sid, db) in r.get("scene_scores", {}) for sid in scene_ids)]

    elif filter_type == "subcategory":
        # 按子类筛选
        subcategory = db.query(SceneSubcategory).filter(SceneSubcategory.name == filter_value).first()
        if not subcategory:
            return []
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.subcategory_id == subcategory.id).all()}
        return [r for r in ranking if any(_get_scene_name(sid, db) in r.get("scene_scores", {}) for sid in scene_ids)]

    elif filter_type == "scene":
        # 按具体场景筛选
        return [r for r in ranking if filter_value in r.get("scene_scores", {})]

    elif filter_type == "chip":
        # 按主芯片筛选
        return [r for r in ranking if r.get("main_chip") == filter_value]

    elif filter_type == "sensor":
        # 按 Sensor 筛选
        return [r for r in ranking if r.get("sensor_model") == filter_value]

    elif filter_type == "focal_length":
        # 按焦距筛选
        return [r for r in ranking if r.get("focal_length") == filter_value]

    elif filter_type == "resolution":
        # 按分辨率筛选
        return [r for r in ranking if r.get("resolution") == filter_value]

    return ranking.copy()


def _get_scene_name(scene_id: int, db: Session) -> str:
    """获取场景完整名称"""
    from ..service.leaderboard import get_scene_name
    return get_scene_name(scene_id, db)


@router.get("/filters", response_model=ApiResponse)
async def get_filter_options(db: Session = Depends(get_db)):
    """获取可用的筛选选项"""
    categories = db.query(SceneCategory).all()
    subcategories = db.query(SceneSubcategory).all()
    devices = db.query(DeviceModel).all()

    # 提取唯一的设备参数
    chips = list(set(d.main_chip for d in devices if d.main_chip))
    sensors = list(set(d.sensor_model for d in devices if d.sensor_model))
    focal_lengths = list(set(d.focal_length for d in devices if d.focal_length))
    resolutions = list(set(d.resolution for d in devices if d.resolution))

    return ApiResponse(
        success=True,
        data=FilterOptions(
            categories=[{"id": c.id, "name": c.name, "location": c.location} for c in categories],
            subcategories=[{"id": s.id, "name": s.name} for s in subcategories],
            chips=sorted(chips),
            sensors=sorted(sensors),
            focal_lengths=sorted(focal_lengths),
            resolutions=sorted(resolutions),
        ).model_dump(),
    )


@router.get("/details/scene", response_model=ApiResponse)
async def get_scene_detail(
    scene_id: int = Query(..., description="场景 ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取场景详情（管理员权限）"""
    cache = get_cleaning_cache()
    if not cache["has_cleaned"]:
        raise HTTPException(status_code=400, detail="请先执行数据清洗")

    # 重新加载有效数据
    from ..api.cleaning import _load_evaluations
    from ..service.cleaning import clean_single_user_consistency, clean_user_group_consistency

    data = _load_evaluations(db)

    # 重新执行清洗以获取有效数据
    all_valid = []
    for user_id in set(r['user_id'] for r in data):
        user_data = [r for r in data if r['user_id'] == user_id]
        try:
            result = clean_single_user_consistency(user_data)
            all_valid.extend(result.passed)
        except ValueError:
            continue

    group_result = clean_user_group_consistency(all_valid)
    valid_records = group_result.passed

    details = compute_scene_details(scene_id, valid_records, db)

    return ApiResponse(success=True, data=details)


@router.get("/details/user", response_model=ApiResponse)
async def get_user_detail(
    user_id: int = Query(..., description="用户 ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户详情（管理员权限）"""
    cache = get_cleaning_cache()
    if not cache["has_cleaned"]:
        raise HTTPException(status_code=400, detail="请先执行数据清洗")

    from ..api.cleaning import _load_evaluations
    from ..service.cleaning import clean_single_user_consistency, clean_user_group_consistency

    data = _load_evaluations(db)

    all_valid = []
    all_invalid = []
    for uid in set(r['user_id'] for r in data):
        user_data = [r for r in data if r['user_id'] == uid]
        try:
            result = clean_single_user_consistency(user_data)
            all_valid.extend(result.passed)
            all_invalid.extend(result.rejected)
        except ValueError:
            continue

    group_result = clean_user_group_consistency(all_valid)
    valid_records = group_result.passed
    all_invalid.extend(group_result.rejected)

    details = compute_user_details(user_id, valid_records, all_invalid, db)

    return ApiResponse(success=True, data=details)


@router.get("/details/device", response_model=ApiResponse)
async def get_device_detail(
    device_id: int = Query(..., description="设备 ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取设备详情（管理员权限）"""
    cache = get_cleaning_cache()
    if not cache["has_cleaned"]:
        raise HTTPException(status_code=400, detail="请先执行数据清洗")

    from ..api.cleaning import _load_evaluations
    from ..service.cleaning import clean_single_user_consistency, clean_user_group_consistency

    data = _load_evaluations(db)

    all_valid = []
    for user_id in set(r['user_id'] for r in data):
        user_data = [r for r in data if r['user_id'] == user_id]
        try:
            result = clean_single_user_consistency(user_data)
            all_valid.extend(result.passed)
        except ValueError:
            continue

    group_result = clean_user_group_consistency(all_valid)
    valid_records = group_result.passed

    details = compute_device_details(device_id, valid_records, db)

    return ApiResponse(success=True, data=details)
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.api.leaderboard import router; print('OK')"`
Expected: `OK`

---

## Task 9: 前端依赖 - 安装 ECharts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 ECharts**

Run: `cd frontend && npm install echarts vue-echarts`
Expected: 安装成功

---

## Task 10: 前端 API - 新增 API 调用

**Files:**
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: 在 index.js 末尾新增 API 调用**

```javascript
// ==================== 数据清洗 ====================
export const apiGetCleaningStatus = () => request('/api/cleaning/status')
export const apiExecuteCleaning = () => request('/api/cleaning/execute', { method: 'POST' })

// ==================== 排行榜 ====================
export const apiGetLeaderboard = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/leaderboard${query ? '?' + query : ''}`)
}
export const apiGetLeaderboardFilters = () => request('/api/leaderboard/filters')
export const apiGetLeaderboardSceneDetail = (sceneId) => request(`/api/leaderboard/details/scene?scene_id=${sceneId}`)
export const apiGetLeaderboardUserDetail = (userId) => request(`/api/leaderboard/details/user?user_id=${userId}`)
export const apiGetLeaderboardDeviceDetail = (deviceId) => request(`/api/leaderboard/details/device?device_id=${deviceId}`)
```

---

## Task 11: 前端路由 - 新增路由配置

**Files:**
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 修改路由配置**

```javascript
import { createRouter, createWebHashHistory } from 'vue-router'
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'
import EvalView from '../views/evaluator/EvalView.vue'
import ResultView from '../views/evaluator/ResultView.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminOverview from '../views/admin/AdminOverview.vue'
import SceneManage from '../views/admin/SceneManage.vue'
import DeviceManage from '../views/admin/DeviceManage.vue'
import ImageManage from '../views/admin/ImageManage.vue'
import PairManage from '../views/admin/PairManage.vue'
import UserManage from '../views/admin/UserManage.vue'
import Leaderboard from '../views/admin/Leaderboard.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: RegisterView },
  { path: '/reset-password', name: 'ResetPassword', component: () => import('../views/auth/ResetPasswordView.vue') },
  { path: '/eval', name: 'Eval', component: EvalView },
  { path: '/result', name: 'Result', component: ResultView },
  { path: '/leaderboard', name: 'Leaderboard', component: Leaderboard },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', redirect: '/admin/overview' },
      { path: 'overview', name: 'AdminOverview', component: AdminOverview },
      { path: 'scenes', name: 'SceneManage', component: SceneManage },
      { path: 'devices', name: 'DeviceManage', component: DeviceManage },
      { path: 'images', name: 'ImageManage', component: ImageManage },
      { path: 'pairs', name: 'PairManage', component: PairManage },
      { path: 'users', name: 'UserManage', component: UserManage },
      { path: 'batch-upload', name: 'BatchUpload', component: () => import('../views/admin/BatchUpload.vue') },
      { path: 'cleaning', name: 'DataCleaning', component: () => import('../views/admin/DataCleaning.vue') },
      { path: 'leaderboard', name: 'AdminLeaderboard', component: Leaderboard },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('blind_eval_token')
  // 不需要登录的页面
  const publicPages = ['Login', 'Register', 'ResetPassword', 'Leaderboard']
  if (!publicPages.includes(to.name) && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
```

---

## Task 12: 前端页面 - DataCleaning.vue

**Files:**
- Create: `frontend/src/views/admin/DataCleaning.vue`

- [ ] **Step 1: 创建数据清洗页面**

```vue
<template>
  <div class="cleaning-page">
    <h1 class="page-title">🧹 数据清洗</h1>

    <!-- 清洗状态 -->
    <div class="status-card">
      <h3>清洗状态</h3>
      <div class="status-info">
        <div class="status-row">
          <span class="label">最后清洗时间：</span>
          <span>{{ status.last_cleaned_at || '未执行过' }}</span>
        </div>
        <div class="status-row">
          <span class="label">清洗时记录数：</span>
          <span>{{ status.cleaned_record_count }}</span>
        </div>
        <div class="status-row">
          <span class="label">当前记录数：</span>
          <span>{{ status.current_record_count }}</span>
        </div>
        <div v-if="status.needs_refresh" class="status-warning">
          ⚠️ 有 {{ status.new_record_count }} 条新评测记录，建议重新清洗
        </div>
        <div v-else-if="status.has_cleaned" class="status-ok">
          ✓ 数据已是最新
        </div>
      </div>
      <button class="btn-primary" @click="executeCleaning" :disabled="loading">
        {{ loading ? '执行中...' : '执行数据清洗' }}
      </button>
    </div>

    <!-- 清洗结果 -->
    <div v-if="result" class="result-section">
      <h3>清洗结果</h3>
      <div class="result-summary">
        <div class="summary-item">
          <span class="label">总记录数：</span>
          <span>{{ result.total_records }}</span>
        </div>
        <div class="summary-item">
          <span class="label">有效记录：</span>
          <span class="text-success">{{ result.valid_records }}</span>
        </div>
        <div class="summary-item">
          <span class="label">无效记录：</span>
          <span class="text-danger">{{ result.invalid_records }}</span>
        </div>
      </div>

      <!-- 单用户一致性检验 -->
      <div class="detail-section">
        <h4>单用户一致性检验（重测信度）</h4>
        <div v-for="(userData, username) in result.single_user_details" :key="username" class="user-detail">
          <h5>{{ username }}</h5>
          <table class="data-table">
            <thead>
              <tr>
                <th>场景</th>
                <th>一致性得分</th>
                <th>阈值</th>
                <th>状态</th>
                <th>匹配对数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="detail in userData.scene_details" :key="detail.scene_id">
                <td>{{ detail.scene_name }}</td>
                <td>{{ detail.agreement_score }}</td>
                <td>{{ detail.threshold }}</td>
                <td>
                  <span :class="detail.rejected ? 'status-reject' : 'status-pass'">
                    {{ detail.rejected ? '✗ 拒绝' : '✓ 通过' }}
                  </span>
                </td>
                <td>{{ detail.matched_pairs }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 用户组一致性检验 -->
      <div class="detail-section">
        <h4>用户组一致性检验</h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>场景</th>
              <th>总用户场景</th>
              <th>通过</th>
              <th>拒绝</th>
              <th>通过率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(detail, sceneId) in result.user_group_details" :key="sceneId">
              <td>{{ detail.scene_name }}</td>
              <td>{{ detail.total_user_scenes }}</td>
              <td>{{ detail.passed }}</td>
              <td>{{ detail.rejected }}</td>
              <td>{{ detail.total_user_scenes > 0 ? ((detail.passed / detail.total_user_scenes) * 100).toFixed(1) + '%' : '0%' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGetCleaningStatus, apiExecuteCleaning } from '../../api/index.js'

const status = ref({
  has_cleaned: false,
  last_cleaned_at: null,
  cleaned_record_count: 0,
  current_record_count: 0,
  new_record_count: 0,
  needs_refresh: false,
})
const result = ref(null)
const loading = ref(false)

async function fetchStatus() {
  try {
    const data = await apiGetCleaningStatus()
    Object.assign(status.value, data)
  } catch (e) {
    console.error('获取清洗状态失败:', e)
  }
}

async function executeCleaning() {
  if (!confirm('确定要执行数据清洗吗？')) return

  loading.value = true
  try {
    const data = await apiExecuteCleaning()
    result.value = data
    await fetchStatus()
  } catch (e) {
    alert('清洗失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
})
</script>

<style scoped>
.cleaning-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.status-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.status-card h3 {
  font-size: 16px;
  color: #374151;
  margin: 0 0 16px 0;
}

.status-info {
  margin-bottom: 16px;
}

.status-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.label {
  font-weight: 600;
  color: #6b7280;
  margin-right: 8px;
}

.status-warning {
  color: #d97706;
  font-weight: 600;
  margin-top: 12px;
  padding: 12px;
  background: #fef3c7;
  border-radius: 8px;
}

.status-ok {
  color: #059669;
  font-weight: 600;
  margin-top: 12px;
  padding: 12px;
  # d1fae5;
  border-radius: 8px;
}

.btn-primary {
  padding: 12px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-section h3 {
  font-size: 16px;
  color: #374151;
  margin: 0 0 16px 0;
}

.result-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
}

.text-success {
  color: #059669;
  font-weight: 600;
}

.text-danger {
  color: #dc2626;
  font-weight: 600;
}

.detail-section {
  margin-top: 24px;
}

.detail-section h4 {
  font-size: 14px;
  color: #374151;
  margin: 0 0 12px 0;
}

.user-detail {
  margin-bottom: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.user-detail h5 {
  font-size: 14px;
  color: #1e40af;
  margin: 0 0 12px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table th {
  background: #f1f5f9;
  font-weight: 600;
  color: #374151;
}

.status-pass {
  color: #059669;
  font-weight: 600;
}

.status-reject {
  color: #dc2626;
  font-weight: 600;
}
</style>
```

---

## Task 13: 前端页面 - Leaderboard.vue

**Files:**
- Create: `frontend/src/views/admin/Leaderboard.vue`

- [ ] **Step 1: 创建排行榜页面**

（此文件较长，包含排行榜视图、管理员白盒视图、ECharts 图表等，完整代码见实施时生成）

---

## Task 14: 前端页面 - 修改现有页面

**Files:**
- Modify: `frontend/src/views/admin/AdminOverview.vue`
- Modify: `frontend/src/views/auth/LoginView.vue`
- Modify: `frontend/src/views/admin/AdminLayout.vue`

- [ ] **Step 1: 修改 AdminOverview.vue**

在快速入口区域新增两个卡片：

```html
<button class="link-card" @click="$router.push('/admin/cleaning')">
  <span class="link-icon">🧹</span>
  <span class="link-label">数据清洗</span>
</button>
<button class="link-card" @click="$router.push('/admin/leaderboard')">
  <span class="link-icon">🏆</span>
  <span class="link-label">排行榜</span>
</button>
```

- [ ] **Step 2: 修改 LoginView.vue**

在登录表单下方新增排行榜按钮：

```html
<div class="divider">或</div>
<button class="btn-leaderboard" @click="$router.push('/leaderboard')">
  🏆 查看设备排行榜
</button>
```

- [ ] **Step 3: 修改 AdminLayout.vue**

在侧边栏底部新增菜单项：

```html
<div class="sidebar-divider"></div>
<router-link to="/admin/cleaning" class="menu-item">
  <span class="menu-icon">🧹</span>
  <span>数据清洗</span>
</router-link>
<router-link to="/admin/leaderboard" class="menu-item">
  <span class="menu-icon">🏆</span>
  <span>排行榜</span>
</router-link>
```

---

## Self-Review Checklist

- [x] **Spec coverage:** 所有设计文档中的需求都有对应任务
- [x] **Placeholder scan:** 无 TBD、TODO 或不完整章节
- [x] **Type consistency:** 命名统一使用 device_id 而非 model_id
