# CS2 智能交易平台 - 监控配置

## 监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                      监控组件                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │ Prometheus│◄──│  Node   │   │  Grafana │               │
│  │          │   │ Exporter │   │          │               │
│  └──────────┘   └──────────┘   └──────────┘               │
│       │                                    │               │
│       ▼                                    ▼               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  业务指标                              │  │
│  │  • API 请求延迟                                       │  │
│  │  • 订单成功率                                         │  │
│  │  • Steam API 熔断状态                                 │  │
│  │  • Redis 缓存命中率                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Prometheus 配置

### 安装

```bash
# Docker 方式
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cs2-platform'
    static_configs:
      - targets: ['backend:8000']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

## 应用指标

### 自定义指标

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 请求计数器
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# 活跃连接
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# 熔断器状态
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['name']
)

# 订单统计
orders_total = Counter(
    'orders_total',
    'Total orders processed',
    ['status', 'side']
)
```

### 指标端点

```python
# app/api/v1/endpoints/metrics.py
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

## Grafana 配置

### 安装

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -v grafana_data:/var/lib/grafana \
  grafana/grafana
```

### 关键仪表盘

#### 1. API 性能

| 指标 | 描述 |
|------|------|
| 请求速率 | 每秒请求数 |
| 延迟 P50/P95/P99 | 响应时间分布 |
| 错误率 | 5xx 错误比例 |

#### 2. 业务指标

| 指标 | 描述 |
|------|------|
| 订单数 | 买入/卖出订单统计 |
| 交易额 | 总体交易量 |
| 库存价值 | 当前库存估值 |

#### 3. 基础设施

| 指标 | 描述 |
|------|------|
| CPU 使用率 | 系统负载 |
| 内存使用 | 已用/可用内存 |
| Redis 内存 | 缓存占用 |

## 日志配置

### 结构化日志

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)
```

### 日志聚合

```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 使用 Loki
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
```

## 告警规则

### Alertmanager 配置

```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://your-alert-webhook'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

### 告警规则示例

```yaml
# rules/alerts.yml
groups:
  - name: cs2-platform
    rules:
      # API 高延迟
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 延迟过高"
          
      # 熔断器开启
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "熔断器已开启: {{ $labels.name }}"
          
      # 订单失败率高
      - alert: HighOrderFailureRate
        expr: rate(orders_total{status="failed"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
```

## 健康检查

### 端点实现

```python
# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    health = {
        "status": "healthy",
        "checks": {}
    }
    
    # 检查数据库
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    # 检查 Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        health["checks"]["redis"] = "ok"
    except Exception as e:
        health["checks"]["redis"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
```

### 就绪检查

```python
@router.get("/ready")
async def readiness_check():
    """检查服务是否就绪"""
    return {"ready": True}
```

## 性能监控

### 关键指标

| 指标 | 正常范围 | 警告阈值 | 严重阈值 |
|------|----------|----------|----------|
| API 延迟 P99 | < 500ms | > 1s | > 2s |
| CPU 使用率 | < 50% | > 70% | > 90% |
| 内存使用率 | < 60% | > 80% | > 90% |
| Redis 内存 | < 300MB | > 400MB | > 500MB |
| 错误率 | < 1% | > 5% | > 10% |

### 监控脚本

```python
# scripts/monitor.py
import asyncio
import redis.asyncio as redis
from sqlalchemy import text
from app.core.config import settings
from app.core.database import async_session_factory

async def check_health():
    results = {"status": "healthy"}
    
    # 数据库检查
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as e:
        results["database"] = str(e)
        results["status"] = "unhealthy"
    
    # Redis 检查
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = str(e)
        results["status"] = "unhealthy"
    
    return results

if __name__ == "__main__":
    print(asyncio.run(check_health()))
```
