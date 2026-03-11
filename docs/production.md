# CS2 智能交易平台 - 生产环境配置

## 环境变量配置

### 必需配置

```env
# 应用
APP_ENV=production
DEBUG=False
SECRET_KEY=<生成一个强密钥>

# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/cs2

# Redis
REDIS_URL=redis://localhost:6379/0

# 认证
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### 可选配置

```env
# Steam API（可选）
STEAM_API_KEY=your-steam-api-key
STEAM_WEB_API_KEY=your-web-api-key

# BUFF API（可选）
BUFF_COOKIE=your-buff-cookie
BUFF_API_KEY=your-buff-api-key

# 邮件配置（可选）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@example.com

# 监控和日志
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO

# 性能优化
WORKERS=4
MAX_CONNECTIONS=100
```

## 数据库优化

### PostgreSQL 配置 (postgresql.conf)

```conf
# 连接配置
max_connections = 100

# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB

# 日志配置
log_min_duration_statement = 1000
log_connections = on
log_disconnections = on

# 查询优化
random_page_cost = 1.1
effective_io_concurrency = 200

# WAL 配置
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### SQLite 配置（WAL 模式）

项目已自动配置 WAL 模式，优化参数：
- `PRAGMA journal_mode=WAL` - 提高并发性能
- `PRAGMA busy_timeout=30000` - 30秒等待锁
- `PRAGMA synchronous=NORMAL` - 平衡性能和安全
- `PRAGMA cache_size=-2000` - 2MB 缓存
- `PRAGMA mmap_size=268435456` - 256MB 内存映射

## Redis 配置

### redis.conf 优化

```conf
# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000

# 日志
loglevel notice

# 连接
timeout 300
tcp-keepalive 60
```

## 后端优化

### Gunicorn 配置

```bash
# 启动命令
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile -
```

### Worker 数量计算

```python
# 推荐公式
workers = (2 * CPU核心数) + 1

# 示例：4 核 CPU
workers = (2 * 4) + 1 = 9
```

## 前端优化

### Nginx 缓存配置

```nginx
server {
    # 静态资源缓存
    location /static {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 资源压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
}
```

### 构建优化

```bash
# 前端构建
cd frontend
npm run build

# 或使用 Vite
npm run build -- --mode production
```

## 安全配置

### CORS 配置

```python
# app/core/config.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 速率限制

```python
# app/api/v1/middleware/rate_limit.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 实现速率限制逻辑
    pass
```

### 安全头

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
```

## 监控配置

### 健康检查端点

```python
# app/api/v1/endpoints/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Prometheus 指标

```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_LATENCY = Histogram('http_request_latency_seconds', 'HTTP request latency')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 备份策略

### 数据库备份

```bash
# PostgreSQL
pg_dump -U user cs2 > backup_$(date +%Y%m%d).sql

# SQLite
cp cs2.db backup_cs2_$(date +%Y%m%d).db
```

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
pg_dump -U user cs2 > /backups/cs2_$DATE.sql
find /backups -type f -mtime +7 -delete
```

## SSL/TLS 配置

### Let's Encrypt

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```
