# 数据清洗与排行榜功能设计文档

## 概述

本文档描述将 `clean_and_stats` 模块合并到主后端，并新增排行榜功能的完整设计。

### 核心决策

1. **数据清洗结果**：不落库存储，写入 evaluations 表（is_valid, reject_type, reject_detail），支持导出报告
2. **排行榜数据**：存储在 leaderboard_ranking 表，重启不丢失
3. **排行榜入口**：登录页（`/ranking`）+ 管理侧边栏（`/admin/leaderboard`）
4. **得分展示**：双指标（BT 得分 + 评分均值）
5. **筛选方式**：支持 category、location、subcategory、scene、chip、sensor、focal_length、resolution
6. **清洗参数**：前端页面可配置，不持久化存储
7. **权限控制**：普通用户只看排行榜，管理员可看详细数据

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端 (Vue 3)                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   AdminOverview │  DataCleaning   │         Leaderboard         │
│   (入口卡片)     │  (清洗页面)      │  (共享页面+权限控制)         │
└────────┬────────┴────────┬────────┴───────────────┬─────────────┘
         │                 │                        │
         ▼                 ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 路由层 (FastAPI)                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ /api/admin/*    │ /api/cleaning/* │       /api/leaderboard/*    │
│ (现有管理API)    │ (数据清洗API)    │         (排行榜API)          │
└────────┬────────┴────────┬────────┴───────────────┬─────────────┘
         │                 │                        │
         ▼                 ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层 (Service)                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  AdminService   │  CleaningService│      LeaderboardService     │
│  (现有)          │  (迁移自         │  (新 - BT计算 + 数据库存储)  │
│                 │   clean_and_stats)│                            │
└────────┬────────┴────────┬────────┴───────────────┬─────────────┘
         │                 │                        │
         ▼                 ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     数据访问层 (SQLAlchemy)                       │
├─────────────────────────────────────────────────────────────────┤
│  Evaluation │ ImagePair │ DeviceModel │ Scene │ LeaderboardRanking│
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、数据库设计

### 2.1 evaluations 表新增字段

```sql
ALTER TABLE evaluations
ADD COLUMN is_valid TINYINT DEFAULT 1 COMMENT '清洗后是否有效 1=有效 0=无效',
ADD COLUMN reject_type VARCHAR(50) DEFAULT NULL COMMENT '拒绝类型: retest_reliability/group_consensus/insufficient_retest',
ADD COLUMN reject_detail JSON DEFAULT NULL COMMENT '拒绝详情';
```

#### reject_type 枚举值

| 值 | 含义 | 说明 |
|----|------|------|
| `retest_reliability` | 重测信度不通过 | 单用户一致性检验不通过 |
| `group_consensus` | 用户组共识不通过 | 用户组一致性检验不通过 |
| `insufficient_retest` | 复评数据不足 | 复评对数不足 10% |

#### reject_detail 示例

**单用户一致性拒绝**：
```json
{
  "scene_id": 1,
  "scene_name": "车库(B4车库)-白天",
  "retest_agreement_score": 0.65,
  "retest_agreement_threshold": 0.70,
  "retest_hard_reject_threshold": 0.55,
  "retest_matched_pairs": 6
}
```

**用户组一致性拒绝**：
```json
{
  "scene_id": 1,
  "scene_name": "车库(B4车库)-白天",
  "group_pearson_r": 0.42,
  "group_dynamic_threshold": 0.55
}
```

**数据不足拒绝**：
```json
{
  "retest_count": 3,
  "total_pairs": 50,
  "required_retest": 5
}
```

### 2.2 leaderboard_ranking 表（新增）

```sql
CREATE TABLE leaderboard_ranking (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- 筛选维度
    filter_type VARCHAR(50) NOT NULL COMMENT '筛选类型: overall/category/location/subcategory/scene/chip/sensor/focal_length/resolution',
    filter_value VARCHAR(200) DEFAULT NULL COMMENT '筛选值',

    -- 设备基础信息
    device_id INT NOT NULL,
    device_name VARCHAR(100),

    -- 高频筛选字段
    main_chip VARCHAR(100),
    sensor_model VARCHAR(100),
    focal_length VARCHAR(50),
    resolution VARCHAR(50),

    -- 扩展属性
    device_attrs JSON COMMENT '设备扩展属性',

    -- 得分
    bt_score FLOAT COMMENT 'BT得分',
    mean_score FLOAT COMMENT '评分均值',
    rank_position INT COMMENT '排名',

    -- 分场景得分
    scene_scores JSON COMMENT '分场景得分 {"场景名": {"bt_score": xx, "mean_score": xx, "eval_count": xx}, ...}',

    -- 管理员详细数据
    detail_data JSON COMMENT '详细评测数据',

    -- 元数据
    total_devices INT NOT NULL DEFAULT 0 COMMENT '参评设备数',
    cleaned_record_count INT NOT NULL DEFAULT 0 COMMENT '清洗时有效记录数',
    last_cleaned_at DATETIME NOT NULL COMMENT '最后清洗时间',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_filter_device (filter_type, filter_value, device_id),
    INDEX idx_rank (filter_type, filter_value, rank_position),
    INDEX idx_device (device_id)
);
```

---

## 三、后端结构

### 3.1 目录结构

```
backend/
├── app/
│   ├── api/
│   │   ├── cleaning.py        ← 重写：数据清洗 API
│   │   ├── leaderboard.py     ← 新增：排行榜 API
│   │   └── ...
│   ├── services/
│   │   ├── cleaning_service.py        ← 重写：合并 cleaner.py + statistics.py
│   │   ├── leaderboard_service.py     ← 新增：排行榜计算 + 数据库存储
│   │   └── ...
│   ├── schemas/
│   │   ├── cleaning.py        ← 重写：清洗请求/响应模型
│   │   ├── leaderboard.py     ← 新增：排行榜数据模型
│   │   └── ...
│   ├── models/
│   │   ├── leaderboard.py     ← 新增：leaderboard_ranking ORM 模型
│   │   └── ...
│   └── core/
│       ├── config.py          ← 新增：清洗参数默认值
│       └── ...
```

### 3.2 文件迁移映射

| 源文件 (clean_and_stats) | 目标文件 (backend) | 说明 |
|--------------------------|-------------------|------|
| app/service/cleaner.py | app/services/cleaning_service.py | 完整迁移 |
| app/service/statistics.py | app/services/cleaning_service.py | 合并 |
| app/core/config.py | app/core/config.py | 合并清洗参数 |
| app/models/schemas.py | app/schemas/cleaning.py | 重写 |

### 3.3 命名规范

| clean_and_stats 命名 | 主干代码命名 | 说明 |
|---------------------|-------------|------|
| model_id | device_id | 设备 ID |
| model_name | device_name | 设备名称 |
| model_a_id | device_a_id | 图对中设备 A 的 ID |
| model_b_id | device_b_id | 图对中设备 B 的 ID |
| MIN_MODELS_* | MIN_DEVICES_* | 最小设备数配置 |

---

## 四、数据清洗模块

### 4.1 清洗流程

```
管理员点击"执行数据清洗"
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第一步：加载数据                                                 │
│                                                                 │
│ 从数据库查询所有 submitted 状态的评测记录：                       │
│ SELECT e.*, ip.scene_id, ip.device_a_id, ip.device_b_id         │
│ FROM evaluations e                                              │
│ JOIN image_pairs ip ON e.pair_id = ip.id                        │
│ WHERE e.status = 'submitted'                                    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第二步：单用户一致性检验（重测信度）                              │
│                                                                 │
│ 1. 按 user_id 分组                                              │
│ 2. 分离原始评分和复评数据（is_repeat 字段）                      │
│ 3. 检查复评比例 >= 10%                                          │
│ 4. 逐场景计算加权 Agreement                                     │
│ 5. 逐场景判定：                                                 │
│    - matched_pairs == 0 → 拒绝                                  │
│    - agreement_score >= threshold → 通过                         │
│    - agreement_score < hard_reject → 硬拒绝                      │
│    - 灰色地带 [0.55, 0.70) → 拒绝                               │
│ 6. 标记无效记录（复评记录被标记）                                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第三步：用户组一致性检验                                         │
│                                                                 │
│ 1. 剔除复评数据，仅保留首次评测                                  │
│ 2. 评分归一化（2.0 → 1.0）                                      │
│ 3. 逐 (user, scene) 计算 log-BT Pearson r                       │
│ 4. 计算动态阈值                                                 │
│ 5. 判定：r < threshold → 拒绝                                   │
│ 6. 标记无效记录                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第四步：更新 evaluations 表                                     │
│                                                                 │
│ 1. 将清洗结果写入 evaluations 表：                              │
│    - is_valid = 0/1                                             │
│    - reject_type = 'retest_reliability'/'group_consensus'/...   │
│    - reject_detail = {...}                                      │
│ 2. 返回清洗结果给管理员                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 清洗参数配置

前端页面可配置的参数：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| 重测一致性阈值 | 0.70 | 0.50-0.90 | agreement_score >= 此值则通过 |
| 重测硬拒绝阈值 | 0.55 | 0.30-0.70 | agreement_score < 此值直接拒绝 |
| 用户组最大阈值 | 0.85 | 0.60-1.00 | 动态阈值的上限 |
| 复评比例要求 | 10% | 5%-30% | 复评对数占总对数的最低比例 |
| 最小设备数 | 2 | 2-10 | 计算相关系数所需的最小设备数 |

**配置逻辑**：
- 后端代码中设置默认值
- 前端页面可修改参数
- 参数随清洗请求传递给后端
- 不持久化存储，下次打开页面恢复默认值

### 4.3 API 接口

#### POST /api/cleaning/execute

执行数据清洗（管理员权限）。

**请求**：
```json
{
  "params": {
    "retest_agreement_threshold": 0.70,
    "retest_hard_reject_threshold": 0.55,
    "group_max_threshold": 0.85,
    "retest_ratio": 0.10,
    "min_devices_per_scene": 2
  }
}
```

**响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_records": 1500,
    "valid_records": 1350,
    "invalid_records": 150,
    "single_user_details": {
      "user1": {
        "scene_details": [
          {
            "scene_id": 1,
            "scene_name": "车库(B4车库)-白天",
            "retest_agreement_score": 0.85,
            "retest_agreement_threshold": 0.70,
            "rejected": false,
            "retest_matched_pairs": 8
          }
        ]
      }
    },
    "user_group_details": {
      "1": {
        "scene_name": "车库(B4车库)-白天",
        "total_user_scenes": 15,
        "passed": 13,
        "rejected": 2
      }
    },
    "leaderboard_updated": true
  }
}
```

#### GET /api/cleaning/defaults

获取清洗参数默认值。

**响应**：
```json
{
  "code": 0,
  "data": {
    "retest_agreement_threshold": 0.70,
    "retest_hard_reject_threshold": 0.55,
    "group_max_threshold": 0.85,
    "retest_ratio": 0.10,
    "min_devices_per_scene": 2
  }
}
```

#### GET /api/cleaning/status

获取当前清洗状态。

**响应**：
```json
{
  "code": 0,
  "data": {
    "has_cleaned": true,
    "last_cleaned_at": "2026-06-10T10:30:00",
    "cleaned_record_count": 1500,
    "current_record_count": 1580,
    "new_record_count": 80,
    "needs_refresh": true
  }
}
```

#### GET /api/cleaning/export

导出清洗报告（管理员权限）。

**响应**：TXT 文件下载

---

## 五、排行榜模块

### 5.1 排行榜计算流程

```
管理员执行数据清洗
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第一步：加载有效数据                                             │
│                                                                 │
│ 从数据库查询 evaluations.is_valid = 1 的记录                     │
│ JOIN image_pairs 获取 scene_id, device_a_id, device_b_id        │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第二步：计算 BT 得分（严格按照 clean_and_stats 算法）            │
│                                                                 │
│ 1. 对所有有效数据运行 Bradley-Terry 模型                        │
│    - 映射规则：score_a > score_b → A 胜 (1.0)                   │
│    - score_a < score_b → B 胜 (1.0)                             │
│    - 相等 → 各计 0.5 胜                                         │
│    - MM 算法迭代，最多 1000 次，收敛阈值 1e-6                   │
│    - 几何均值归一化为 1                                         │
│                                                                 │
│ 2. 得到每个 device_id 的 BT 强度值                              │
│                                                                 │
│ 3. 归一化到 0-100 分                                            │
│    bt_score = (bt_strength / max_bt_strength) * 100             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第三步：计算评分均值                                             │
│                                                                 │
│ 对每个 device，计算所有有效评分的均值                            │
│ mean_score = mean(所有 score_a + score_b)                       │
│ 归一化到 0-100 分                                               │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第四步：分场景计算得分                                           │
│                                                                 │
│ 对每个 scene，单独计算：                                        │
│ - 该场景下的 BT 强度                                            │
│ - 该场景下的评分均值                                            │
│ - 该场景下的评测次数                                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第五步：生成筛选组合                                             │
│                                                                 │
│ 生成所有筛选维度的排行榜数据：                                   │
│ - overall（综合）                                                │
│ - category（大类）                                               │
│ - location（地点）                                               │
│ - subcategory（子类）                                            │
│ - scene（具体场景）                                              │
│ - chip（主芯片）                                                 │
│ - sensor（Sensor）                                               │
│ - focal_length（焦距）                                           │
│ - resolution（分辨率）                                           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 第六步：写入 leaderboard_ranking 表                              │
│                                                                 │
│ 每个筛选组合 × 每个设备 = 一条记录                              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 筛选维度

| 筛选类型 | filter_type | filter_value 示例 | 筛选逻辑 |
|---------|-------------|-------------------|----------|
| 综合得分 | overall | null | 所有场景的 BT 得分综合 |
| 按大类 | category | "车库" | 筛选 category.name='车库' 的所有 scene |
| 按地点 | location | "B4车库" | 筛选 category.location='B4车库' 的所有 scene |
| 按子类 | subcategory | "白天" | 筛选 subcategory.name='白天' 的所有 scene |
| 按具体场景 | scene | "车库(B4车库)-白天" | 单个 scene |
| 按主芯片 | chip | "Hi3516EV300" | 筛选 device.main_chip='Hi3516EV300' |
| 按Sensor | sensor | "IMX307" | 筛选 device.sensor_model='IMX307' |
| 按焦距 | focal_length | "4mm" | 筛选 device.focal_length='4mm' |
| 按分辨率 | resolution | "1080P" | 筛选 device.resolution='1080P' |

**筛选逻辑示例**：

```
按 category 筛选"车库"：
1. SELECT id FROM scene_categories WHERE name = '车库' → category_id=1
2. SELECT id FROM scenes WHERE category_id = 1 → [1, 2, 3, 4]
3. 基于这些 scene_id 聚合评测数据，计算 BT 得分

按 location 筛选"B4车库"：
1. SELECT id FROM scene_categories WHERE location = 'B4车库' → category_id=1
2. SELECT id FROM scenes WHERE category_id = 1 → [1, 2, 3, 4]
3. 基于这些 scene_id 聚合评测数据，计算 BT 得分

按 subcategory 筛选"白天"：
1. SELECT id FROM scene_subcategories WHERE name = '白天' → subcategory_id=1
2. SELECT id FROM scenes WHERE subcategory_id = 1 → [1, 5, 9]
3. 基于这些 scene_id 聚合评测数据，计算 BT 得分
```

### 5.3 API 接口

#### GET /api/leaderboard

获取排行榜数据（无需登录）。

**查询参数**：
- `filter_type`: 筛选类型
- `filter_value`: 筛选值
- `score_type`: 得分类型（bt/mean），默认 bt

**响应**：
```json
{
  "code": 0,
  "data": {
    "ranking": [
      {
        "rank": 1,
        "device_id": 5,
        "device_name": "682-A4 1.0",
        "main_chip": "Hi3516EV300",
        "sensor_model": "IMX307",
        "focal_length": "4mm",
        "resolution": "1080P",
        "bt_score": 85.2,
        "mean_score": 82.5,
        "bt_rank": 1,
        "mean_rank": 2,
        "rank_diff": 1,
        "scene_scores": {
          "车库(B4车库)-白天": {"bt_score": 88.0, "mean_score": 85.2, "eval_count": 45},
          "车库(B4车库)-低照": {"bt_score": 82.0, "mean_score": 80.5, "eval_count": 42}
        }
      }
    ],
    "filter_info": {
      "type": "overall",
      "value": null
    },
    "total_devices": 20,
    "last_updated": "2026-06-10T10:30:00"
  }
}
```

#### GET /api/leaderboard/filters

获取可用的筛选选项（无需登录）。

**响应**：
```json
{
  "code": 0,
  "data": {
    "categories": [
      {"id": 1, "name": "车库", "location": "B4车库"},
      {"id": 2, "name": "公园树荫", "location": "32楼花园"}
    ],
    "subcategories": [
      {"id": 1, "name": "白天"},
      {"id": 2, "name": "低照"},
      {"id": 3, "name": "夜晚红外"},
      {"id": 4, "name": "夜晚白光"}
    ],
    "chips": ["Hi3516EV300", "Hi3516DV300"],
    "sensors": ["IMX307", "IMX335"],
    "focal_lengths": ["4mm", "6mm"],
    "resolutions": ["1080P", "4K"]
  }
}
```

#### GET /api/leaderboard/details

获取详细评测数据（管理员权限）。

**查询参数**：
- `view_type`: 视图类型（scene/user/device）
- `id`: 具体 ID

**响应（按场景）**：
```json
{
  "code": 0,
  "data": {
    "view_type": "scene",
    "scene": {
      "id": 1,
      "name": "车库(B4车库)-白天",
      "total_records": 150,
      "valid_records": 135,
      "invalid_records": 15,
      "invalid_users": ["user1", "user5", "user8"]
    },
    "device_ranking": [
      {
        "rank": 1,
        "device_id": 1,
        "device_name": "682-A4 1.0",
        "eval_count": 45,
        "mean_score": 85.2,
        "bt_strength": 1.5,
        "bt_rank": 1,
        "mean_rank": 2,
        "rank_diff": 1
      }
    ],
    "invalid_users_by_scene": [
      {"scene_id": 1, "scene_name": "车库(B4车库)-白天", "invalid_count": 3},
      {"scene_id": 2, "scene_name": "车库(B4车库)-低照", "invalid_count": 2}
    ]
  }
}
```

**响应（按用户）**：
```json
{
  "code": 0,
  "data": {
    "view_type": "user",
    "user": {
      "id": 1,
      "username": "user1",
      "total_evals": 120,
      "first_evals": 100,
      "retest_evals": 20,
      "retest_rate": 0.20,
      "passed_scenes": 8,
      "rejected_scenes": 2,
      "pass_rate": 0.80
    },
    "scene_details": [
      {
        "scene_id": 1,
        "scene_name": "车库(B4车库)-白天",
        "eval_count": 20,
        "retest_agreement_score": 0.85,
        "retest_agreement_threshold": 0.70,
        "passed": true
      }
    ]
  }
}
```

**响应（按设备）**：
```json
{
  "code": 0,
  "data": {
    "view_type": "device",
    "device": {
      "id": 1,
      "name": "682-A4 1.0"
    },
    "scenes": [
      {
        "scene_id": 1,
        "scene_name": "车库(B4车库)-白天",
        "bt_score": 88.0,
        "mean_score": 85.2,
        "eval_count": 45
      }
    ]
  }
}
```

#### GET /api/leaderboard/export

导出排行榜数据（管理员权限）。

**查询参数**：
- `export_type`: 导出类型（ranking/detail）
- `filter_type`: 筛选类型
- `filter_value`: 筛选值
- `view_type`: 视图类型（仅 detail 类型需要，支持 scene/user/device）

**响应**：TXT 文件下载

---

## 六、前端设计

### 6.1 页面清单

| 页面 | 文件 | 权限 | 说明 |
|-----|------|------|------|
| 数据清洗 | DataCleaning.vue | 管理员 | 新增 |
| 排行榜 | Leaderboard.vue | 无需登录 | 新增（管理员有额外功能） |
| 管理概览 | AdminOverview.vue | 管理员 | 新增入口卡片 |
| 登录页 | LoginView.vue | 无需登录 | 利用现有 /ranking 链接 |
| 管理布局 | AdminLayout.vue | 管理员 | 侧边栏新增菜单项 |

### 6.2 路由配置

```javascript
// 新增路由（无需登录）
{
  path: '/ranking',
  name: 'Leaderboard',
  component: Leaderboard,
  meta: { public: true }
},

// 管理后台子路由
{ path: 'cleaning', name: 'DataCleaning', component: DataCleaning },
{ path: 'leaderboard', name: 'AdminLeaderboard', component: Leaderboard },
```

### 6.3 路由守卫调整

```javascript
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
```

### 6.4 权限控制

排行榜页面使用同一组件，根据用户角色动态显示 tab：

```vue
<template>
  <div class="leaderboard-page">
    <!-- 标签页 -->
    <div class="tabs">
      <button
        :class="{ active: activeTab === 'ranking' }"
        @click="activeTab = 'ranking'"
      >
        排行榜
      </button>
      <button
        v-if="authStore.isAdmin"
        :class="{ active: activeTab === 'detail' }"
        @click="activeTab = 'detail'"
      >
        详细数据
      </button>
    </div>

    <!-- 内容区 -->
    <div v-if="activeTab === 'ranking'">
      <!-- 排行榜内容（普通用户和管理员都可见） -->
    </div>

    <div v-if="activeTab === 'detail' && authStore.isAdmin">
      <!-- 详细数据内容（仅管理员可见） -->
    </div>
  </div>
</template>
```

### 6.5 AdminOverview 新增入口

在快速入口区域新增两个卡片：
- 🧹 数据清洗 → `/admin/cleaning`
- 🏆 排行榜 → `/admin/leaderboard`

### 6.6 AdminLayout 侧边栏

在侧边栏底部新增分隔线和菜单项：
```
─────────────
🧹 数据清洗
🏆 排行榜
─────────────
🚪 退出
```

### 6.7 数据清洗页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  🧹 数据清洗                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────┬─────────────────────────┐ │
│  │ 清洗参数配置                     │ 清洗状态                 │ │
│  ├─────────────────────────────────┼─────────────────────────┤ │
│  │ 重测一致性阈值：[0.70] ●─────── │ 最后清洗时间：10:30:00  │ │
│  │ 重测硬拒绝阈值：[0.55] ●─────── │ 清洗时记录数：1500      │ │
│  │ 用户组最大阈值：[0.85] ●─────── │ 当前记录数：1580        │ │
│  │ 复评比例要求：  [10%]  ●─────── │ ⚠️ 有 80 条新记录       │ │
│  │ 最小设备数：    [2]    ●─────── │                         │ │
│  │                                 │                         │ │
│  │ [恢复默认值]                     │                         │ │
│  └─────────────────────────────────┴─────────────────────────┘ │
│                                                                 │
│  [执行数据清洗]  [导出清洗报告]                                  │
│                                                                 │
│  单用户一致性检验（重测信度）                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │用户  │场景                    │一致性得分│阈值 │状态│重测对数│   │
│  ├──────┼────────────────────────┼─────────┼─────┼────┼───────┤   │
│  │user1 │车库(B4车库)-白天       │0.85     │0.70 │ ✓  │ 8     │   │
│  │user1 │车库(B4车库)-低照       │0.62     │0.70 │ ✗  │ 6     │   │
│  └──────┴────────────────────────┴─────────┴─────┴────┴───────┘   │
│                                                                 │
│  用户组一致性检验                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │场景                      │总用户场景│通过│拒绝│通过率      │   │
│  ├──────────────────────────┼─────────┼────┼────┼───────────┤   │
│  │车库(B4车库)-白天         │ 15      │ 13 │ 2  │ 86.7%     │   │
│  │车库(B4车库)-低照         │ 12      │ 11 │ 1  │ 91.7%     │   │
│  └──────────────────────────┴─────────┴────┴────┴───────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.8 排行榜页面布局

#### 普通用户/管理员 共享视图（tab1：排行榜）

```
┌─────────────────────────────────────────────────────────────────┐
│  🏆 设备排行榜                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 筛选条件（紧凑排列，与图表联动）                          │   │
│  │                                                         │   │
│  │ 得分类型：[BT得分 ▼]                                     │   │
│  │                                                         │   │
│  │ 场景：[全部场景 ▼]  大类：[全部 ▼]  子类：[全部 ▼]       │   │
│  │                                                         │   │
│  │ 主芯片：[全部 ▼]  Sensor：[全部 ▼]  焦距：[全部 ▼]      │   │
│  │                                                         │   │
│  │ [重置筛选]                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 排行榜图表（筛选条件变化，图表实时更新）                  │   │
│  │                                                         │   │
│  │  1. 682-A4 1.0    ████████████████████████████ 85.2    │   │
│  │  2. 682-B2 1.0    ██████████████████████████  82.1    │   │
│  │  3. 682-C3 1.0    ████████████████████████   78.5    │   │
│  │  ...                                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 排行榜表格                                               │   │
│  │                                                         │   │
│  │ │排名│设备名      │主芯片      │Sensor │综合得分│       │   │
│  │ ├───┼────────────┼───────────┼───────┼───────┤       │   │
│  │ │ 1 │682-A4 1.0  │Hi3516EV300│IMX307 │ 85.2  │       │   │
│  │ │ 2 │682-B2 1.0  │Hi3516EV300│IMX307 │ 82.1  │       │   │
│  │ └───┴────────────┴───────────┴───────┴───────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 雷达图（分场景得分对比）                                  │   │
│  │                                                         │   │
│  │                    白天                                  │   │
│  │                     ▲                                   │   │
│  │                    /|\                                  │   │
│  │         夜晚白光 ──┼── 低照                             │   │
│  │                    \|/                                  │   │
│  │                     ▼                                   │   │
│  │                  夜晚红外                                │   │
│  │                                                         │   │
│  │  ── 682-A4  ── 682-B2  ── 682-C3                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 管理员视图（tab2：详细数据）

```
┌─────────────────────────────────────────────────────────────────┐
│  🏆 设备排行榜                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [排行榜] [详细数据]  ← 管理员可见两个 tab                      │
│                                                                 │
│  [导出排行榜结果] [导出详细数据]  ← 导出按钮                    │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│  详细数据标签页                                                  │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  维度选择：[按场景] [按用户] [按设备]                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 按场景查看：                                             │   │
│  │                                                         │   │
│  │ 场景：[车库(B4车库)-白天 ▼]                              │   │
│  │                                                         │   │
│  │ 场景统计                                                 │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ 总评测记录数：150                                    │ │   │
│  │ │ 有效记录数：135                                      │ │   │
│  │ │ 剔除记录数：15                                       │ │   │
│  │ │ 剔除用户数：3                                        │ │   │
│  │ │ 剔除用户列表：user1, user5, user8                    │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ 设备排行                                                 │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │排名│设备名      │评测次数│评分均值│BT强度│BT排名│均值排名│排名差│ │   │
│  │ ├───┼────────────┼───────┼───────┼──────┼──────┼───────┼──────┤ │   │
│  │ │ 1 │682-A4 1.0  │ 45    │ 85.2  │ 1.5  │ 1    │ 2     │ +1   │ │   │
│  │ │ 2 │682-B2 1.0  │ 42    │ 83.0  │ 1.2  │ 2    │ 1     │ -1   │ │   │
│  │ │ 3 │682-C3 1.0  │ 48    │ 80.5  │ 0.9  │ 3    │ 3     │ 0    │ │   │
│  │ └───┴────────────┴───────┴───────┴──────┴──────┴───────┴──────┘ │   │
│  │                                                         │   │
│  │ 各场景剔除用户数统计                                     │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │场景                      │总记录│有效│剔除│剔除用户数│ │   │
│  │ ├──────────────────────────┼──────┼────┼────┼──────────┤ │   │
│  │ │车库(B4车库)-白天         │ 150  │ 135│ 15 │ 3        │ │   │
│  │ │车库(B4车库)-低照         │ 120  │ 108│ 12 │ 2        │ │   │
│  │ │公园树荫(32楼花园)-白天   │ 140  │ 130│ 10 │ 2        │ │   │
│  │ └──────────────────────────┴──────┴────┴────┴──────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 按用户查看：                                             │   │
│  │                                                         │   │
│  │ 用户：[user1 ▼]                                         │   │
│  │                                                         │   │
│  │ 用户统计                                                 │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ 总评测数：120                                        │ │   │
│  │ │ 首次评测数：100                                      │ │   │
│  │ │ 重测数：20                                           │ │   │
│  │ │ 重测率：20%                                          │ │   │
│  │ │ 通过场景数：8                                        │ │   │
│  │ │ 拒绝场景数：2                                        │ │   │
│  │ │ 通过率：80%                                          │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ 各场景一致性                                             │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │场景                    │评测对数│一致性得分│阈值 │状态│ │   │
│  │ ├────────────────────────┼───────┼─────────┼─────┼────┤ │   │
│  │ │车库(B4车库)-白天       │ 20    │ 0.85    │ 0.70│ ✓  │ │   │
│  │ │车库(B4车库)-低照       │ 18    │ 0.62    │ 0.70│ ✗  │ │   │
│  │ │公园树荫(32楼花园)-白天 │ 22    │ 0.78    │ 0.70│ ✓  │ │   │
│  │ └────────────────────────┴───────┴─────────┴─────┴────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 按设备查看：                                             │   │
│  │                                                         │   │
│  │ 设备：[682-A4 1.0 ▼]                                    │   │
│  │                                                         │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │场景                    │BT得分│评分均值│评测次数     │ │   │
│  │ ├────────────────────────┼──────┼───────┼─────────────┤ │   │
│  │ │车库(B4车库)-白天       │ 88.0 │ 85.2  │ 45          │ │   │
│  │ │车库(B4车库)-低照       │ 82.0 │ 80.5  │ 42          │ │   │
│  │ │公园树荫(32楼花园)-白天 │ 85.0 │ 83.0  │ 48          │ │   │
│  │ └────────────────────────┴──────┴───────┴─────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、图表库选型

推荐使用 **ECharts**：

| 特性 | 说明 |
|------|------|
| 柱状图 | 横向柱状图展示设备得分对比 |
| 雷达图 | 展示各设备在不同场景下的表现 |
| 交互支持 | 点击、缩放、tooltip |
| Vue 集成 | 有 vue-echarts 组件，集成简单 |
| 文档完善 | 中文文档，社区活跃 |

安装：
```bash
npm install echarts vue-echarts
```

---

## 八、实施计划

### 阶段一：后端迁移（数据清洗）

1. 迁移 cleaner.py + statistics.py → backend/app/services/cleaning_service.py
2. 合并清洗参数到 backend/app/core/config.py
3. 重写 backend/app/schemas/cleaning.py
4. 重写 backend/app/api/cleaning.py
5. 修改 evaluations 表结构

### 阶段二：后端新增（排行榜）

1. 新增 backend/app/models/leaderboard.py
2. 新增 backend/app/services/leaderboard_service.py
3. 新增 backend/app/schemas/leaderboard.py
4. 新增 backend/app/api/leaderboard.py

### 阶段三：前端新增

1. 安装 ECharts
2. 新增 DataCleaning.vue
3. 新增 Leaderboard.vue
4. 修改 AdminOverview.vue
5. 修改 AdminLayout.vue
6. 修改 router/index.js
7. 修改 api/index.js
