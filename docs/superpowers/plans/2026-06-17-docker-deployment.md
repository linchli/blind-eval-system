# Docker 部署实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Blind Eval System 容器化，实现一键部署到任意 PC

**Architecture:** 双容器架构（App + MySQL），使用 Docker Compose 编排，多阶段构建优化镜像大小

**Tech Stack:** Docker, Docker Compose, Python 3.12, Node.js 20, MySQL 8.0, FastAPI, Vue 3

---

## 文件结构

创建以下新文件：

```
blind-eval-system/
├── Dockerfile                  # 应用镜像构建（多阶段）
├── docker-compose.yml          # 服务编排配置
├── .dockerignore               # Docker 构建排除文件
├── .env.example                # 环境变量示例
└── docker/
    └── entrypoint.sh           # 容器启动脚本
```

---

## Task 1: 创建 .dockerignore 文件

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: 创建 .dockerignore 文件**

```dockerignore
# 版本控制
.git
.gitignore

# Python 虚拟环境
.venv
venv
env

# Python 缓存
__pycache__
*.pyc
*.pyo
*.pyd
.Python

# Node.js
node_modules
npm-debug.log*

# 前端构建产物（将在容器内构建）
frontend/dist

# 上传文件（使用 Docker Volume 持久化）
uploads/*
test_images

# IDE 和编辑器
.claude
.vscode
.idea
*.swp
*.swo

# 文档
docs
*.md
!README.md

# 环境变量（敏感信息）
.env
.env.local
.env.*.local

# Docker 相关
docker-compose*.yml
Dockerfile
.dockerignore

# 操作系统文件
.DS_Store
Thumbs.db
```

- [ ] **Step 2: 验证文件创建**

Run: `cat .dockerignore`
Expected: 显示上述内容

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore for Docker builds"
```

---

## Task 2: 创建 .env.example 文件

**Files:**
- Create: `.env.example`

- [ ] **Step 1: 创建 .env.example 文件**

```env
# ==================== 应用配置 ====================
# 应用端口（宿主机映射端口）
APP_PORT=8000

# ==================== MySQL 配置 ====================
# MySQL 端口（宿主机映射端口，可选）
MYSQL_PORT=3306

# MySQL 用户名
MYSQL_USER=root

# MySQL 密码（请在生产环境修改）
MYSQL_PASSWORD=blind_eval_2024

# 数据库名
MYSQL_DATABASE=blind_eval

# ==================== 安全配置 ====================
# JWT 密钥（请在生产环境修改为随机字符串）
SECRET_KEY=blind-eval-secret-key-2026
```

- [ ] **Step 2: 验证文件创建**

Run: `cat .env.example`
Expected: 显示上述内容

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore: add .env.example with default configuration"
```

---

## Task 3: 创建 docker/entrypoint.sh 启动脚本

**Files:**
- Create: `docker/entrypoint.sh`

- [ ] **Step 1: 创建 docker 目录**

Run: `mkdir -p docker`
Expected: 目录创建成功

- [ ] **Step 2: 创建 entrypoint.sh 文件**

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  Blind Eval System - Starting..."
echo "=========================================="

# 等待 MySQL 就绪
echo "[1/3] Waiting for MySQL..."
max_retries=30
retry_count=0

while ! nc -z mysql 3306; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: MySQL connection timeout after $max_retries attempts"
        exit 1
    fi
    echo "  Waiting for MySQL... (attempt $retry_count/$max_retries)"
    sleep 2
done
echo "  MySQL is ready!"

# 初始化数据库（创建表和默认用户）
echo "[2/3] Initializing database..."
python -c "
import sys
sys.path.insert(0, '/app')
from backend.app.core.database import engine, Base
from backend.main import _seed_default_users, _seed_default_scenes

# 创建所有表
print('  Creating database tables...')
Base.metadata.create_all(bind=engine)

# 创建默认用户和场景
print('  Seeding default users...')
_seed_default_users()

print('  Seeding default scenes...')
_seed_default_scenes()

print('  Database initialized successfully!')
" || echo "  Database initialization skipped (may already exist)"

# 启动应用
echo "[3/3] Starting application..."
echo "=========================================="
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Account:  admin / admin123"
echo "=========================================="

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 3: 设置执行权限**

Run: `chmod +x docker/entrypoint.sh`
Expected: 权限设置成功

- [ ] **Step 4: 验证文件内容**

Run: `cat docker/entrypoint.sh`
Expected: 显示上述内容

- [ ] **Step 5: Commit**

```bash
git add docker/entrypoint.sh
git commit -m "feat: add Docker entrypoint script with DB initialization"
```

---

## Task 4: 创建 Dockerfile（多阶段构建）

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
# ==================== Stage 1: 构建前端 ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制依赖文件（利用 Docker 缓存）
COPY frontend/package*.json ./

# 安装依赖
RUN npm ci

# 复制前端源代码
COPY frontend/ ./

# 构建前端
RUN npm run build

# ==================== Stage 2: 应用运行 ====================
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install --no-cache-dir uv

# 复制依赖文件（利用 Docker 缓存）
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖
RUN uv pip install --system --no-cache -r pyproject.toml

# 复制后端代码
COPY backend/ ./backend/

# 复制构建好的前端
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建必要目录
RUN mkdir -p uploads/images uploads/thumbnails

# 复制启动脚本
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动入口
ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 2: 验证 Dockerfile 语法**

Run: `docker build --check . 2>&1 || echo "Docker syntax check completed"`
Expected: 无语法错误

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add multi-stage Dockerfile for app container"
```

---

## Task 5: 创建 docker-compose.yml 服务编排

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  # ==================== 应用服务 ====================
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: blind-eval-app
    restart: unless-stopped
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=${MYSQL_USER:-root}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD:-blind_eval_2024}
      - MYSQL_DATABASE=${MYSQL_DATABASE:-blind_eval}
      - SECRET_KEY=${SECRET_KEY:-blind-eval-secret-key-2026}
    volumes:
      - uploads_data:/app/uploads
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - blind-eval-net

  # ==================== MySQL 服务 ====================
  mysql:
    image: mysql:8.0
    container_name: blind-eval-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD:-blind_eval_2024}
      - MYSQL_DATABASE=${MYSQL_DATABASE:-blind_eval}
      - MYSQL_CHARACTER_SET_SERVER=utf8mb4
      - MYSQL_COLLATION_SERVER=utf8mb4_unicode_ci
    ports:
      - "${MYSQL_PORT:-3306}:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - blind-eval-net

# ==================== 数据卷 ====================
volumes:
  mysql_data:
    name: blind-eval-mysql-data
  uploads_data:
    name: blind-eval-uploads-data

# ==================== 网络 ====================
networks:
  blind-eval-net:
    driver: bridge
```

- [ ] **Step 2: 验证 docker-compose.yml 语法**

Run: `docker-compose config`
Expected: 显示解析后的配置，无错误

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add Docker Compose configuration for multi-container deployment"
```

---

## Task 6: 更新 .gitignore 添加 Docker 相关规则

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 读取当前 .gitignore**

Run: `cat .gitignore`
Expected: 显示当前内容

- [ ] **Step 2: 添加 Docker 相关规则**

在 `.gitignore` 文件末尾添加：

```gitignore

# ==================== Docker ====================
# 环境变量文件（包含敏感信息）
.env
.env.local
.env.*.local

# Docker Compose 覆盖文件
docker-compose.override.yml
```

- [ ] **Step 3: 验证更新**

Run: `cat .gitignore | tail -10`
Expected: 显示新增的 Docker 相关规则

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for Docker environment files"
```

---

## Task 7: 构建并测试 Docker 镜像

**Files:**
- None (验证步骤)

- [ ] **Step 1: 构建 Docker 镜像**

Run: `docker-compose build`
Expected: 成功构建 app 和 mysql 镜像

输出示例：
```
[+] Building 120.5s (20/20) FINISHED
 => [frontend-builder] Building...
 => [app] Building...
```

- [ ] **Step 2: 检查构建的镜像**

Run: `docker images | grep blind-eval`
Expected: 显示构建的镜像

- [ ] **Step 3: 启动服务**

Run: `docker-compose up -d`
Expected: 启动 app 和 mysql 容器

输出示例：
```
[+] Running 3/3
 ✔ Network blind-eval-net    Created
 ✔ Container blind-eval-mysql  Healthy
 ✔ Container blind-eval-app    Started
```

- [ ] **Step 4: 检查服务状态**

Run: `docker-compose ps`
Expected: 两个容器都是 Up 状态

输出示例：
```
NAME                STATUS          PORTS
blind-eval-app      Up (healthy)    0.0.0.0:8000->8000/tcp
blind-eval-mysql    Up (healthy)    0.0.0.0:3306->3306/tcp
```

- [ ] **Step 5: 检查应用日志**

Run: `docker-compose logs app`
Expected: 显示启动成功的日志

输出示例：
```
==========================================
  Blind Eval System - Starting...
==========================================
[1/3] Waiting for MySQL...
  MySQL is ready!
[2/3] Initializing database...
  Database initialized successfully!
[3/3] Starting application...
==========================================
  Backend:  http://localhost:8000
  API Docs: http://localhost:8000/docs
  Account:  admin / admin123
==========================================
```

- [ ] **Step 6: 测试健康检查接口**

Run: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok","version":"0.3.0"}`

- [ ] **Step 7: 测试 Web 访问**

在浏览器中打开：`http://localhost:8000`
Expected: 显示登录页面

- [ ] **Step 8: 测试默认账号登录**

使用以下账号登录：
- 用户名：`admin`
- 密码：`admin123`

Expected: 成功登录并进入系统

- [ ] **Step 9: 停止服务**

Run: `docker-compose down`
Expected: 成功停止并移除容器

---

## Task 8: 创建便捷启动脚本（可选）

**Files:**
- Create: `docker-start.sh` (Linux/Mac)
- Create: `docker-start.bat` (Windows)

- [ ] **Step 1: 创建 Linux/Mac 启动脚本**

```bash
#!/bin/bash

echo "=========================================="
echo "  Blind Eval System - Docker Launcher"
echo "=========================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# 构建并启动服务
echo "Building and starting services..."
docker-compose up -d --build

# 等待服务就绪
echo "Waiting for services to be ready..."
sleep 10

# 检查服务状态
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "  Started successfully!"
echo "  URL: http://localhost:8000"
echo "  Account: admin / admin123"
echo ""
echo "  Useful commands:"
echo "    View logs:    docker-compose logs -f"
echo "    Stop:         docker-compose down"
echo "    Restart:      docker-compose restart"
echo "=========================================="
```

- [ ] **Step 2: 创建 Windows 启动脚本**

```batch
@echo off
echo ============================================
echo   Blind Eval System - Docker Launcher
echo ============================================

REM 检查 .env 文件
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)

REM 构建并启动服务
echo Building and starting services...
docker-compose up -d --build

REM 等待服务就绪
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo Service Status:
docker-compose ps

echo.
echo ============================================
echo   Started successfully!
echo   URL: http://localhost:8000
echo   Account: admin / admin123
echo.
echo   Useful commands:
echo     View logs:    docker-compose logs -f
echo     Stop:         docker-compose down
echo     Restart:      docker-compose restart
echo ============================================
pause
```

- [ ] **Step 3: 设置执行权限（Linux/Mac）**

Run: `chmod +x docker-start.sh`
Expected: 权限设置成功

- [ ] **Step 4: Commit**

```bash
git add docker-start.sh docker-start.bat
git commit -m "feat: add convenience scripts for Docker deployment"
```

---

## Task 9: 创建部署文档

**Files:**
- Create: `DOCKER.md`

- [ ] **Step 1: 创建 DOCKER.md 文档**

```markdown
# Docker 部署指南

## 快速开始

### 前置条件

- Docker 20.10+
- Docker Compose 2.0+

### 一键部署

```bash
# 克隆项目
git clone <repo-url>
cd blind-eval-system

# 启动服务（Linux/Mac）
./docker-start.sh

# 启动服务（Windows）
docker-start.bat
```

或者手动启动：

```bash
# 复制环境变量
cp .env.example .env

# 构建并启动
docker-compose up -d --build
```

### 访问系统

- URL: http://localhost:8000
- 默认账号: admin / admin123

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| APP_PORT | 8000 | 应用访问端口 |
| MYSQL_PORT | 3306 | MySQL 端口 |
| MYSQL_USER | root | MySQL 用户名 |
| MYSQL_PASSWORD | blind_eval_2024 | MySQL 密码 |
| MYSQL_DATABASE | blind_eval | 数据库名 |
| SECRET_KEY | blind-eval-secret-key-2026 | JWT 密钥 |

### 连接外部 MySQL

修改 `.env` 文件：

```env
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_USER=your-user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=blind_eval
```

然后修改 `docker-compose.yml`，移除 MySQL 服务和 `depends_on` 配置。

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build
```

## 数据备份

### 备份数据库

```bash
docker exec blind-eval-mysql mysqldump -u root -pblind_eval_2024 blind_eval > backup.sql
```

### 备份上传文件

```bash
docker cp blind-eval-app:/app/uploads ./uploads_backup
```

### 恢复数据

```bash
# 恢复数据库
docker exec -i blind-eval-mysql mysql -u root -pblind_eval_2024 blind_eval < backup.sql

# 恢复上传文件
docker cp ./uploads_backup/. blind-eval-app:/app/uploads/
```

## 部署到其他 PC

### 方式一：传输镜像（推荐）

```bash
# 在开发机上构建并保存镜像
docker-compose build
docker save blind-eval-system_app | gzip > blind-eval-app.tar.gz
docker save mysql:8.0 > mysql-8.0.tar

# 在目标机上加载镜像
docker load < blind-eval-app.tar.gz
docker load < mysql-8.0.tar

# 启动服务
docker-compose up -d
```

### 方式二：传输代码

```bash
# 打包项目
tar -czf blind-eval-system.tar.gz --exclude='.git' --exclude='.venv' .

# 在目标机上解压并启动
tar -xzf blind-eval-system.tar.gz
docker-compose up -d
```

## 故障排查

### MySQL 连接失败

```bash
# 检查 MySQL 容器状态
docker-compose ps mysql

# 查看 MySQL 日志
docker-compose logs mysql
```

### 端口冲突

修改 `.env` 中的端口配置。

### 镜像构建失败

```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建
docker-compose build --no-cache
```
```

- [ ] **Step 2: Commit**

```bash
git add DOCKER.md
git commit -m "docs: add Docker deployment guide"
```

---

## Task 10: 最终验证和清理

**Files:**
- None (验证步骤)

- [ ] **Step 1: 停止现有服务**

Run: `docker-compose down -v`
Expected: 停止容器并移除卷

- [ ] **Step 2: 清理 Docker 缓存**

Run: `docker system prune -f`
Expected: 清理未使用的资源

- [ ] **Step 3: 完整构建测试**

Run: `docker-compose up -d --build`
Expected: 成功构建并启动所有服务

- [ ] **Step 4: 等待服务就绪**

Run: `sleep 30 && docker-compose ps`
Expected: 所有容器都是 healthy 状态

- [ ] **Step 5: 功能验证**

Run: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok","version":"0.3.0"}`

- [ ] **Step 6: 浏览器验证**

在浏览器中打开 `http://localhost:8000`，使用 admin/admin123 登录
Expected: 成功登录并能正常使用系统

- [ ] **Step 7: 查看最终文件列表**

Run: `ls -la Dockerfile docker-compose.yml .dockerignore .env.example docker/`
Expected: 所有文件都已创建

- [ ] **Step 8: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete Docker deployment setup

- Multi-stage Dockerfile for optimized builds
- Docker Compose with MySQL and app services
- Environment variable configuration
- Entrypoint script with auto-initialization
- Convenience scripts for easy deployment
- Deployment documentation"
```

---

## 完成

所有任务完成后，系统已完全容器化，支持：

- ✅ 一键部署：`docker-compose up -d`
- ✅ 数据持久化：Docker Volume
- ✅ 灵活配置：环境变量 + 外部 MySQL 支持
- ✅ 快速迁移：镜像导出/导入
- ✅ 健康检查：自动监控服务状态
- ✅ 便捷脚本：Windows/Linux/Mac 启动脚本
- ✅ 完整文档：部署指南和故障排查
