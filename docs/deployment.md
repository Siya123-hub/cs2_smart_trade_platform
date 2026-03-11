# CS2 智能交易平台 - 部署指南

## 系统要求

### 硬件要求
- CPU: 2 核以上
- 内存: 4GB 以上
- 磁盘: 20GB 以上
- 系统: Ubuntu 20.04+ / CentOS 8+ / Debian 11+

### 软件要求
- Python 3.10+
- PostgreSQL 14+ 或 SQLite 3
- Redis 6+
- Node.js 18+ (前端构建)

## 部署方式

### 方式一：Docker 部署（推荐）

#### 1. 安装 Docker
```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### 2. 使用 Docker Compose 部署
```bash
# 克隆项目
git clone https://github.com/your-repo/cs2_platform.git
cd cs2_platform

# 配置环境变量
cp .env.example .env
nano .env

# 启动所有服务
docker-compose up -d
```

#### docker-compose.yml 示例
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/cs2
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=cs2
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 方式二：手动部署

#### 1. 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3-pip postgresql redis-server nginx

# CentOS/RHEL
sudo yum install -y python310 python310-pip postgresql redis nginx
```

#### 2. 创建虚拟环境
```bash
# 克隆项目
git clone https://github.com/your-repo/cs2_platform.git
cd cs2_platform/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置环境变量
```bash
cp .env.example .env
nano .env
```

重要配置项：
```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/cs2
# 或使用 SQLite
DATABASE_URL=sqlite:///./cs2.db

# Redis
REDIS_URL=redis://localhost:6379/0

# 安全密钥
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Steam API（可选）
STEAM_API_KEY=your-steam-api-key
```

#### 4. 初始化数据库
```bash
# 方式一：使用 CLI 工具
python -m app.cli init_db
python -m app.cli create-admin

# 方式二：使用 Alembic
alembic upgrade head
```

#### 5. 配置 Nginx
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/cs2_platform/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 6. 启动服务
```bash
# 启动后端（生产环境推荐使用 Gunicorn + Uvicorn）
pip install gunicorn uvicorn

# 启动
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用 systemd
sudo cp cs2_platform.service /etc/systemd/system/
sudo systemctl start cs2_platform
sudo systemctl enable cs2_platform
```

## 验证部署

### 检查服务状态
```bash
# 检查后端 API
curl http://localhost:8000/api/v1/health

# 检查前端
curl http://localhost:3000

# 检查数据库连接
python -m app.cli test-api
```

### 查看日志
```bash
# Docker
docker-compose logs -f

# Systemd
journalctl -u cs2_platform -f
```

## 常见问题

### 数据库连接失败
1. 检查 PostgreSQL 服务状态
2. 验证数据库凭据
3. 检查防火墙规则

### Redis 连接失败
1. 检查 Redis 服务状态
2. 验证 Redis 配置文件
3. 检查内存是否充足

### 前端加载失败
1. 检查 Nginx 配置
2. 验证静态文件路径
3. 查看浏览器控制台错误
