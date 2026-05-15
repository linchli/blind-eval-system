---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3044022034d2713afb5ab8c14b512fdfccc9db409e06cb5f783a8b83455d26f96497290702206db9acce57e8537ec5554e91440140a17a839aa7e20708a949f36232b76b1d31
    ReservedCode2: 3046022100c247f11f7be08bcf8a190d320ed44fc162887bcd093f4d688b9d023773be70bf022100e251420f2638dc9eaebe90fde481d965dee837a8f35e36b0ac09c55f0de6da28
---

# 图像盲评系统 v0.2

## 快速启动

```bash
# Windows
start.bat

# 或手动启动
python -m backend.init_db  # 初始化数据库
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 评审员 | evaluator1 | eval123 |
| 评审员 | evaluator2 | eval123 |
| 访客 | guest | guest123 |

## API 端点

### 评测核心 API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/eval/status` | 获取评测状态 |
| POST | `/api/eval/start-session` | 开始新会话 |
| POST | `/api/eval/resume-session` | 恢复会话 |
| POST | `/api/eval/submit` | 提交草稿评分 |
| POST | `/api/eval/submit-round` | 整轮提交 |
| GET | `/api/eval/pair/{id}` | 获取图对详情 |

### 管理 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/admin/init-demo` | 初始化演示数据 |
| GET | `/api/admin/scenes` | 获取场景列表 |
| GET | `/api/admin/models` | 获取机型列表 |
| GET | `/api/admin/pairs` | 获取所有图对 |

## 状态机

```
LOADING
  │
  ├──→ NO_PAIRS (暂无数据)
  │
  ├──→ READY_TO_START (开始评测)
  │       │
  │       └──→ IN_SESSION
  │
  ├──→ RESUMABLE (继续评测)
  │       │
  │       └──→ IN_SESSION
  │
  └──→ IN_SESSION ──→ BATCH_COMPLETE ──→ ALL_DONE
                           │
                           └──→ READY_TO_START (再来一轮)
```

## 评测流程

1. **开始评测** → 系统分配 20 对图对创建 Session
2. **逐对评分** → 每次评分即时保存草稿，可修改
3. **全部完成** → 点击"提交结果"锁定所有评分
4. **再来一轮** → 可继续评测下一批图对

## 数据库表结构

- `users` - 用户表
- `scenes` - 场景表
- `models` - 机型表
- `image_pairs` - 图像对表
- `eval_sessions` - 评测会话表 (新增)
- `evaluations` - 评分记录表 (新增草稿机制)

## 技术栈

- 后端: FastAPI + SQLAlchemy + MySQL
- 前端: Vue 3 + Pinia + Vite
- 图像: Pillow 生成演示图
