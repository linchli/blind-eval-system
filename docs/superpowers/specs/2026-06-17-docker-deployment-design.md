# Docker 部署设计方案

## 概述

将 Blind Eval System 容器化，实现一键部署到任意 PC（Windows/Ubuntu），支持快速迁移和演示。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                           │
│                                                             │
│  ┌─────────────────────────────────┐  ┌──────────────────┐  │
│  │        App Container           │  │  MySQL Container │  │
│  │                                 │  │                  │  │
│  │  ┌─────────────┐ ┌───────────┐ │  │   MySQL 8.0      │  │
│  │  │   FastAPI   │ │  静态前端  │ │  │   Port: 3306     │  │
│  │  │  (uvicorn)  │ │  (Vue 3)  │ │  │                  │  │
│  │  └─────────────┘ └───────────┘ │  └──────────────────┘  │
│  │         │                       │           │            │
│  │         └───────────────────────┼───────────┘            │
│  │                                 │                        │
│  │  Port: 8000                     │                        │
│  └─────────────────────────────────┘                        │
│                          │                                  │
│                          ▼                                  │
│                    Docker Volume                            │
│              (mysql_data + uploads)                         │
└─────────────────────────────────────────────────────────────┘
```

### 服务组件

1. **App Container** (blind-eval-app)
   - 基于 Python 3.12
   - 包含 FastAPI 后端 + 构建后的 Vue 前端
   - 暴露端口：8000
   - 环境变量配置数据库连接

2. **MySQL Container** (blind-eval-mysql)
   - 基于 MySQL 8.0
   - 暴露端口：3306（可选）
   - 数据持久化：Docker Volume

## 文件结构

```
blind-eval-system/
├── Dockerfile                  # 应用镜像构建
├── docker-compose.yml          # 服务编排
├── .dockerignore               # 排除不需要的文件
├── .env.example                # 环境变量示例
├── docker/
│   └── entrypoint.sh           # 容器启动脚本
└── ... (existing files)
```

## 详细设计

### 1. Dockerfile

采用多阶段构建，优化镜像大小：

```dockerfile
# Stage 1: 构建前端
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: 应用运行
FROM python:3.12-slim
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖
RUN uv pip install --system -r pyproject.toml

# 复制后端代码
COPY backend/ ./backend/

# 复制构建好的前端
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建必要目录
RUN mkdir -p uploads/images uploads/thumbnails

# 复制启动脚本
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
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
    networks:
      - blind-eval-net

volumes:
  mysql_data:
    name: blind-eval-mysql-data
  uploads_data:
    name: blind-eval-uploads-data

networks:
  blind-eval-net:
    driver: bridge
```

### 3. docker/entrypoint.sh

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  Blind Eval System - Starting..."
echo "=========================================="

# 等待 MySQL 就绪
echo "[1/3] Waiting for MySQL..."
while ! nc -z mysql 3306; do
  sleep 1
done
echo "  MySQL is ready!"

# 初始化数据库（创建表和默认用户）
echo "[2/3] Initializing database..."
python -c "
from backend.app.core.database import engine, Base
from backend.main import _seed_default_users, _seed_default_scenes

# 创建所有表
Base.metadata.create_all(bind=engine)

# 创建默认用户和场景
_seed_default_users()
_seed_default_scenes()
print('  Database initialized successfully')
" 2>/dev/null || echo "  Database already initialized"

# 启动应用
echo "[3/3] Starting application..."
echo "=========================================="
echo "  Backend:  http://localhost:8000"
echo "  Account:  admin / admin123"
echo "=========================================="

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4. .dockerignore

```
.git
.venv
__pycache__
*.pyc
node_modules
dist
uploads/*
test_images
.claude
docs
*.md
.env
.env.local
```

### 5. .env.example

```env
# 应用端口
APP_PORT=8000

# MySQL 配置
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=blind_eval_2024
MYSQL_DATABASE=blind_eval

# JWT 密钥（生产环境请修改）
SECRET_KEY=blind-eval-secret-key-2026
```

## 数据持久化

### Docker Volume

1. **mysql_data**: 存储 MySQL 数据库文件
   - Volume 名称：`blind-eval-mysql-data`
   - 挂载路径：`/var/lib/mysql`

2. **uploads_data**: 存储用户上传的图片
   - Volume 名称：`blind-eval-uploads-data`
   - 挂载路径：`/app/uploads`

### 数据备份

```bash
# 备份数据库
docker exec blind-eval-mysql mysqldump -u root -p blind_eval > backup.sql

# 备份上传文件
docker cp blind-eval-app:/app/uploads ./uploads_backup
```

## 使用方式

### 快速启动（一键部署）

```bash
# 1. 克隆项目（或复制项目文件夹）
git clone <your-repo-url>  # 或直接复制项目文件夹
cd blind-eval-system

# 2. 启动服务
docker-compose up -d

# 3. 访问系统
# 浏览器打开 http://localhost:8000
# 默认账号：admin / admin123
```

### 自定义配置

```bash
# 复制环境变量文件
cp .env.example .env

# 修改配置（如端口、密码等）
vim .env

# 启动服务
docker-compose up -d
```

### 连接外部 MySQL

如果需要连接外部 MySQL，修改 `.env` 文件：

```env
# 使用外部 MySQL
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_USER=your-user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=blind_eval
```

然后修改 `docker-compose.yml`，移除 MySQL 服务和 `depends_on`：

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=${MYSQL_HOST}
      # ... 其他环境变量
    # 移除 depends_on 部分
```

## 镜像构建优化

### 多阶段构建优势

1. **前端构建阶段**：使用 Node.js Alpine 镜像，体积小
2. **应用运行阶段**：使用 Python slim 镜像，只包含运行时依赖
3. **最终镜像大小**：约 300-400MB（不含 MySQL）

### 构建缓存优化

- 先复制依赖文件（pyproject.toml, package.json），再复制源代码
- 利用 Docker 层缓存，依赖不变时无需重新安装

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
# 打包项目（排除不需要的文件）
tar -czf blind-eval-system.tar.gz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='uploads' \
  --exclude='test_images' \
  .

# 在目标机上解压并启动
tar -xzf blind-eval-system.tar.gz
docker-compose up -d
```

## 健康检查

### 应用健康检查

```bash
# 检查服务状态
docker-compose ps

# 检查应用健康
curl http://localhost:8000/api/health

# 查看日志
docker-compose logs -f app
```

### MySQL 健康检查

```bash
# 检查 MySQL 状态
docker exec blind-eval-mysql mysqladmin ping -u root -p

# 连接数据库
docker exec -it blind-eval-mysql mysql -u root -p blind_eval
```

## 故障排查

### 常见问题

1. **MySQL 连接失败**
   - 检查 MySQL 容器是否启动：`docker-compose ps`
   - 查看 MySQL 日志：`docker-compose logs mysql`
   - 确认环境变量配置正确

2. **端口冲突**
   - 修改 `.env` 中的 `APP_PORT` 或 `MYSQL_PORT`
   - 检查端口占用：`netstat -tulpn | grep <port>`

3. **权限问题**
   - 确保 uploads 目录可写
   - 检查 Docker Volume 权限

4. **镜像构建失败**
   - 检查网络连接
   - 尝试使用国内镜像源

## 扩展功能

### 可选：添加 Nginx 反向代理

如果需要 HTTPS 或更好的性能，可以添加 Nginx 服务：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
```

## 总结

本方案提供：

- ✅ 一键部署：`docker-compose up -d`
- ✅ 数据持久化：Docker Volume
- ✅ 灵活配置：支持外部 MySQL
- ✅ 快速迁移：镜像导出/导入
- ✅ 易于维护：清晰的服务结构

预计部署时间：5-10 分钟（取决于网络速度）
