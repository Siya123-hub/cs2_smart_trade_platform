# CS2 智能交易平台 - 故障排查

## 常见问题

### 1. 数据库连接问题

#### 症状：数据库连接失败

```
Error: could not connect to server
```

**排查步骤：**

1. 检查 PostgreSQL 服务状态
```bash
sudo systemctl status postgresql
```

2. 验证连接信息
```bash
psql -h localhost -U user -d cs2 -c "SELECT 1"
```

3. 检查防火墙
```bash
sudo ufw allow 5432/tcp
```

4. 检查连接数限制
```sql
SELECT count(*) FROM pg_stat_activity;
SHOW max_connections;
```

#### 症状：SQLite 锁定

```
Error: database is locked
```

**解决方案：**

1. 项目已配置 WAL 模式，自动解决大部分锁定问题
2. 增加 `busy_timeout`：
```python
await conn.execute(text("PRAGMA busy_timeout=60000"))
```
3. 使用读写分离

---

### 2. Redis 连接问题

#### 症状：Redis 连接失败

```
Error: Connection refused
```

**排查步骤：**

1. 检查 Redis 服务
```bash
sudo systemctl status redis
redis-cli ping
```

2. 检查内存使用
```bash
redis-cli info memory
# 检查 used_memory_human
```

3. 清理过期键
```bash
redis-cli FLUSHDB
```

---

### 3. API 响应问题

#### 症状：请求超时

**排查步骤：**

1. 检查日志
```bash
tail -f logs/app.log | grep timeout
```

2. 检查慢查询
```sql
-- PostgreSQL
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

3. 增加超时配置

#### 症状：返回 500 错误

**排查步骤：**

1. 开启调试模式
```env
DEBUG=True
```

2. 查看详细错误
```bash
curl -v http://localhost:8000/api/v1/your-endpoint
```

3. 检查中间件错误

---

### 4. 熔断器问题

#### 症状：熔断器开启

```
Circuit breaker is OPEN
```

**原因：**
- Steam API 连续失败
- 外部服务不可用

**解决方案：**

1. 查看熔断器状态
```python
from app.core.circuit_breaker import CircuitBreakerDecorator
print(CircuitBreakerDecorator.get_all_stats())
```

2. 手动重置
```python
breaker = CircuitBreakerDecorator.get_breaker("steam")
breaker.reset()
```

3. 检查外部服务状态

---

### 5. 认证问题

#### 症状：Token 过期

```
401 Unauthorized
```

**解决方案：**

1. 检查 Token 配置
```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

2. 使用 Refresh Token 刷新
```python
response = await client.post(
    "/api/v1/auth/refresh",
    json={"refresh_token": "your-refresh-token"}
)
```

#### 症状：Session 无效

**排查步骤：**

1. 检查 Redis Session
```bash
redis-cli KEYS "session:*"
```

2. 检查 Token 映射
```bash
redis-cli KEYS "token:*"
```

---

### 6. 前端问题

#### 症状：页面空白

**排查步骤：**

1. 检查浏览器控制台
2. 验证 Nginx 配置
3. 检查静态文件路径

#### 症状：API 请求失败

**排查步骤：**

1. 检查 CORS 配置
2. 验证 Token 传递
3. 检查网络请求

---

## 日志分析

### 关键日志模式

| 关键词 | 含义 | 建议动作 |
|--------|------|----------|
| `connection refused` | 服务不可用 | 检查服务状态 |
| `timeout` | 请求超时 | 增加超时或优化查询 |
| `locked` | 资源锁定 | 等待或重试 |
| `memory` | 内存问题 | 增加内存或清理缓存 |
| `circuit` | 熔断器 | 检查外部服务 |

### 日志命令

```bash
# 查看最近错误
tail -100 logs/error.log | grep ERROR

# 实时跟踪
tail -f logs/app.log

# 搜索特定错误
grep -r "Exception" logs/

# 按时间过滤
sed -n '/10:00:00/,/10:30:00/p' logs/app.log
```

---

## 性能问题

### 1. 数据库性能

#### 慢查询优化

1. 添加索引
```sql
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

2. 分析查询计划
```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 1;
```

3. 连接池调整
```python
engine = create_async_engine(
    url,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
)
```

### 2. Redis 性能

#### 缓存优化

1. 监控命中率
```bash
redis-cli INFO stats | grep keyspace
```

2. 清理过期键
```bash
redis-cli --scan --pattern "cache:*" | head -100 | xargs redis-cli UNLINK
```

### 3. 内存问题

#### 排查内存泄漏

```python
import tracemalloc

tracemalloc.start()

# ... 运行代码 ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## 故障恢复

### 1. 数据库恢复

```bash
# 停止服务
sudo systemctl stop cs2_platform

# 恢复备份
psql -U user cs2 < backup_20240101.sql

# 启动服务
sudo systemctl start cs2_platform
```

### 2. Redis 恢复

```bash
# 清理所有数据
redis-cli FLUSHDB

# 重启 Redis
sudo systemctl restart redis
```

### 3. 完整重置

```bash
# 使用 CLI 工具
python -m app.cli drop-all
python -m app.cli init-db
python -m app.cli create-admin
python -m app.cli reset-cache
```

---

## 调试技巧

### 1. 启用调试模式

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

### 2. 使用 Python 调试器

```python
import pdb
pdb.set_trace()
```

### 3. SQLAlchemy 查询日志

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 4. 请求追踪

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

@router.get("/debug/{trace_id}")
async def debug_trace(trace_id: str):
    span = trace.get_current_span()
    return {
        "trace_id": trace_id,
        "span_context": span.get_context()
    }
```

---

## 联系支持

当遇到无法解决的问题时：

1. 收集日志
```bash
tar -czf debug_logs.tar.gz logs/
```

2. 收集系统信息
```bash
uname -a
python --version
pip list
```

3. 提交 Issue
   - 提供问题描述
   - 附上日志
   - 说明复现步骤
