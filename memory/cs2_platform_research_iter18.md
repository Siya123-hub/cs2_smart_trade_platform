# CS2智能交易平台 - 第18轮调研报告

## 调研概述
- **调研时间**: 2026-03-11
- **项目**: CS2智能交易平台
- **迭代**: 第18轮
- **目标**: 调研剩余问题可拓展性与鲁棒性

---

## 一、剩余问题详细分析

### P1-1: #6 Buff API 重试退避算法(线性退避无上限)

**问题位置**: `backend/app/services/buff_service.py:60-62`

**问题描述**:
```python
# 当前代码
await asyncio.sleep(self.RETRY_DELAY * retry_count)
# 其中 RETRY_DELAY = 5
```

**问题分析**:
- 当前使用**线性退避**: 5s → 10s → 15s → ...
- 第3次重试后延迟达到15秒，第10次会达到50秒
- 线性退避在高频限流场景下效率低，容易造成**级联失败**
- 无最大延迟上限，长时间故障时会无限等待
- 缺少**抖动(Jitter)**机制，多客户端可能同步重试

**解决方案**:
```python
# 推荐：指数退避 + 抖动
import random

async def _exponential_backoff_with_jitter(retry_count: int, base_delay: float = 5.0, max_delay: float = 60.0):
    """指数退避 + 随机抖动"""
    # 指数增长：5s → 10s → 20s → 40s (最大60s)
    delay = min(base_delay * (2 ** retry_count), max_delay)
    # 添加随机抖动 (0.5 ~ 1.5 倍)
    jitter = delay * (0.5 + random.random())
    return jitter
```

**影响评估**: 高 - 影响API稳定性

---

### P1-2: #7 交易服务返回格式不一致

**问题位置**: 
- `backend/app/services/trading_service.py`
- `backend/app/services/buff_service.py`
- `backend/app/services/steam_service.py`

**问题描述**:
不同服务的返回格式不统一：

| 服务 | 成功返回 | 失败返回 |
|------|----------|----------|
| trading_service.execute_buy | `{"success": bool, "order_id": ..., "price": ...}` | `{"success": False, "message": ...}` |
| buff_service | 直接返回API数据 或 `None` | 抛出异常 |
| steam_service | 直接返回数据 或 `None` | 抛出异常/返回None |

**问题分析**:
1. `trading_service` 使用 `success` 字段包装
2. `buff_service` / `steam_service` 直接返回原始数据
3. 异常处理不一致：有的抛异常，有的返回None

**解决方案**:
```python
# 统一响应格式
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class ServiceResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    code: str = "SUCCESS"  # 业务错误码

# 所有服务方法返回 ServiceResponse
async def execute_buy(...) -> ServiceResponse:
    try:
        ...
        return ServiceResponse(success=True, data={...})
    except Exception as e:
        return ServiceResponse(success=False, error=str(e), code="BUY_FAILED")
```

**影响评估**: 中 - 影响代码可维护性和错误处理

---

### P1-3: #8 Steam API Session 缺少健康检查

**问题位置**: `backend/app/services/steam_service.py`

**问题描述**:
```python
class SteamAPI:
    def __init__(self, ...):
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        # 仅检查 closed 状态
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(...)
        return self._session
```

**问题分析**:
1. 仅检查 `session.closed`，未检查连接是否健康
2. 长时间空闲后，代理/负载均衡器可能关闭连接
3. 无连接存活探测（heartbeat）
4. Session 可能在 `closed=False` 状态下已失效

**解决方案**:
```python
import asyncio

class SteamAPI:
    HEALTH_CHECK_INTERVAL = 300  # 5分钟
    HEALTH_CHECK_URL = "https://api.steampowered.com"
    
    async def _health_check(self) -> bool:
        """健康检查"""
        try:
            # 使用轻量级API检测连接状态
            async with self.session.get(
                f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/",
                params={"key": self.api_key, "steamids": "0"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status in (200, 400)  # 400也说明服务可用
        except:
            return False
    
    async def _ensure_healthy_session(self):
        """确保session健康"""
        if self._session is None or self._session.closed:
            await self._create_session()
        elif not await self._health_check():
            await self._session.close()
            await self._create_session()
```

**影响评估**: 中 - 可能导致长时间运行后API调用失败

---

### P1-4: #9 幂等性 Key 算法(JSON顺序问题)

**问题位置**: `backend/app/core/idempotency.py`

**问题描述**:
```python
def generate_idempotency_key(
    user_id: int,
    method: str,
    path: str,
    request_body: str  # JSON字符串
) -> str:
    key_data = f"{user_id}:{method}:{path}:{request_body}"
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()
```

**问题分析**:
1. `request_body` 是JSON字符串，**不同顺序的JSON会产生不同的hash**
2. 前端可能发送 `{"price": 100, "item_id": 1}` 或 `{"item_id": 1, "price": 100}`
3. 业务上是同一请求，但会被识别为不同请求
4. 当前实现需要调用方保证顺序，不够健壮

**解决方案**:
```python
import json

def generate_idempotency_key(
    user_id: int,
    method: str,
    path: str,
    request_body: str
) -> str:
    # 方法1: 解析JSON后排序序列化
    try:
        body_dict = json.loads(request_body)
        # 递归排序所有嵌套字典
        sorted_body = _recursive_sort(body_dict)
        canonical_body = json.dumps(sorted_body, sort_keys=True, separators=(',', ':'))
    except json.JSONDecodeError:
        # 非JSON内容直接使用
        canonical_body = request_body
    
    key_data = f"{user_id}:{method}:{path}:{canonical_body}"
    return f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(key_data.encode()).hexdigest()}"

def _recursive_sort(obj):
    """递归排序字典"""
    if isinstance(obj, dict):
        return {k: _recursive_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_recursive_sort(item) for item in obj]
    return obj
```

**影响评估**: 中 - 可能导致重复请求未被正确识别

---

### P1-5: #10 审计日志缺少加密存储

**问题位置**: `backend/app/middleware/audit.py`

**问题描述**:
```python
def log(self, request: Request, ...):
    # 当前直接记录到日志（明文）
    log_func = getattr(logger, audit_config["level"], logger.info)
    log_func(f"AUDIT: {audit_entry['action']} - {json.dumps(audit_entry, ensure_ascii=False)}")
```

**问题分析**:
1. 审计日志包含敏感信息（用户ID、IP地址、操作内容）
2. 当前以明文存储到日志系统
3. 日志文件/系统可能被未授权访问
4. 不符合**合规要求**（如PCI-DSS、GDPR）

**解决方案**:
```python
from app.core.encryption import encrypt_sensitive_data, decrypt_sensitive_data

class AuditLogger:
    def __init__(self, encrypt_logs: bool = True):
        self.encrypt_logs = encrypt_logs
    
    def _encrypt_audit_entry(self, entry: dict) -> dict:
        """加密审计日志"""
        if not self.encrypt_logs:
            return entry
        
        # 加密敏感字段
        sensitive_fields = ["user", "client", "request", "response"]
        encrypted_entry = entry.copy()
        
        for field in sensitive_fields:
            if field in entry and entry[field]:
                try:
                    encrypted_entry[field] = encrypt_sensitive_data(
                        json.dumps(entry[field]).encode()
                    ).decode()
                except:
                    encrypted_entry[field] = entry[field]  # 降级处理
        
        return encrypted_entry
    
    def log(self, ...):
        # 构建审计日志
        audit_entry = {...}
        
        # 加密存储
        if self.encrypt_logs:
            audit_entry = self._encrypt_audit_entry(audit_entry)
        
        # 发送到安全的审计存储（数据库/专用日志服务）
        await self._save_to_secure_storage(audit_entry)
```

**额外建议**: 
- 使用专门的审计日志服务（如AWS CloudTrail、阿里云日志审计）
- 实现日志防篡改机制（Merkle树/区块链）
- 分离敏感日志的访问权限

**影响评估**: 高 - 安全合规风险

---

## 二、系统可拓展性优化方向

### 2.1 新增交易对支持

**当前架构**:
```python
# 硬编码的交易对
if buy_platform == "buff" and sell_platform == "steam":
    # 搬砖逻辑
```

**优化方案 - 插件化交易对**:
```python
from abc import ABC, abstractmethod

class TradingPair(ABC):
    """交易对基类"""
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def buy_platform(self) -> str:
        pass
    
    @property
    @abstractmethod
    def sell_platform(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, item_id: int, quantity: int) -> ServiceResponse:
        pass

# 注册交易对
class BuffToSteam(TradingPair):
    name = "buff_steam"
    buy_platform = "buff"
    sell_platform = "steam"
    
    async def execute(self, item_id: int, quantity: int) -> ServiceResponse:
        # 实现搬砖逻辑
        ...

# 交易对注册表
TRADING_PAIRS: Dict[str, TradingPair] = {
    "buff_steam": BuffToSteam(),
    "steam_buff": SteamToBuff(),
    # 未来可扩展
    "buff_dmarket": BuffToDMarket(),
    "dmarket_steam": DMarketToSteam(),
}

# 新增交易对只需注册
def register_trading_pair(name: str, pair: TradingPair):
    TRADING_PAIRS[name] = pair
```

**扩展支持的市场**:
| 市场 | API类型 | 优先级 |
|------|---------|--------|
| DMarket | REST API | 高 |
| Skinport | REST API | 中 |
| CSGOEmpire | WebSocket | 中 |
| BitSkins | REST API | 低 |

---

### 2.2 插件化架构

**当前问题**: 功能耦合度高，扩展困难

**优化方案 - 微内核架构**:
```
┌─────────────────────────────────────────────────────────┐
│                     Core Platform                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  调度器   │  │  规则引擎 │  │  事件总线 │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
           ▲              ▲              ▲
           │              │              │
    ┌──────┴──────┐ ┌─────┴─────┐ ┌──────┴──────┐
    │ Buff插件    │ │ Steam插件 │ │ DMarket插件│
    └─────────────┘ └───────────┘ └────────────┘
           ▲              ▲              ▲
           │              │              │
    ┌──────┴──────────────┴──────────────┴──────┐
    │              插件接口 (Plugin API)         │
    │  - get_market_price(item_id)              │
    │  - create_order(item_id, price, side)    │
    │  - get_inventory()                        │
    │  - health_check()                         │
    └───────────────────────────────────────────┘
```

```python
# plugin_system.py
from pluggy import PluginManager

class MarketPlugin(ABC):
    """市场插件接口"""
    
    @abstractmethod
    async def get_price(self, market_hash_name: str) -> Optional[PriceInfo]:
        pass
    
    @abstractmethod
    async def create_order(self, item_id: int, price: float, side: str) -> OrderResult:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass

# 插件管理器
plugin_manager = PluginManager('market_plugins')
plugin_manager.register(BuffPlugin())
plugin_manager.register(SteamPlugin())

# 使用插件
price = await plugin_manager.get_plugin('buff').get_price(...)
```

---

### 2.3 配置热更新

**当前问题**: 配置需重启应用生效

**解决方案**:
```python
# config_manager.py
from pydantic import BaseModel
from typing import Dict, Any, Callable

class ConfigManager:
    """配置热更新管理器"""
    
    def __init__(self):
        self._configs: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable]] = {}
    
    async def load_from_redis(self, key: str):
        """从Redis加载配置"""
        redis = await get_redis()
        config_data = await redis.get(f"config:{key}")
        if config_data:
            self._configs[key] = json.loads(config_data)
            await self._notify_listeners(key)
    
    async def watch_config(self, key: str, callback: Callable):
        """监听配置变化"""
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
    
    async def _notify_listeners(self, key: str):
        """通知监听器"""
        for callback in self._listeners.get(key, []):
            await callback(self._configs.get(key))

# 使用示例
config_manager = ConfigManager()

# 启动时加载
await config_manager.load_from_redis("trading")
await config_manager.load_from_redis("rate_limits")

# 监听变化
async def on_trading_config_change(new_config):
    logger.info(f"交易配置已更新: {new_config}")
    
await config_manager.watch_config("trading", on_trading_config_change)

# 动态更新（通过管理API）
@app.patch("/admin/config/{key}")
async def update_config(key: str, config: dict):
    await redis.set(f"config:{key}", json.dumps(config))
    await config_manager.load_from_redis(key)  # 触发热更新
```

---

## 三、鲁棒性测试用例设计

### 3.1 单元测试

#### 3.1.1 幂等性Key生成测试
```python
# tests/test_idempotency.py
import pytest
from app.core.idempotency import generate_idempotency_key

class TestIdempotencyKey:
    """幂等性Key生成测试"""
    
    def test_json_order_independent(self):
        """测试JSON顺序不影响key生成"""
        body1 = '{"price": 100, "item_id": 1}'
        body2 = '{"item_id": 1, "price": 100}'
        
        key1 = generate_idempotency_key(1, "POST", "/api/v1/orders", body1)
        key2 = generate_idempotency_key(1, "POST", "/api/v1/orders", body2)
        
        assert key1 == key2
    
    def test_nested_json_order_independent(self):
        """测试嵌套JSON顺序不影响key生成"""
        body1 = '{"order": {"price": 100, "items": [1, 2, 3]}}'
        body2 = '{"order": {"items": [1, 2, 3], "price": 100}}'
        
        key1 = generate_idempotency_key(1, "POST", "/api/v1/orders", body1)
        key2 = generate_idempotency_key(1, "POST", "/api/v1/orders", body2)
        
        assert key1 == key2
    
    def test_different_user_different_key(self):
        """测试不同用户生成不同key"""
        key1 = generate_idempotency_key(1, "POST", "/api/v1/orders", '{"price": 100}')
        key2 = generate_idempotency_key(2, "POST", "/api/v1/orders", '{"price": 100}')
        
        assert key1 != key2
```

#### 3.1.2 指数退避测试
```python
# tests/test_backoff.py
import pytest
import asyncio
from app.services.utils import exponential_backoff_with_jitter

class TestExponentialBackoff:
    """指数退避测试"""
    
    def test_max_delay_cap(self):
        """测试最大延迟上限"""
        delays = []
        for retry in range(10):
            delay = exponential_backoff_with_jitter(retry, base_delay=1, max_delay=10)
            delays.append(delay)
        
        # 所有延迟不应超过max_delay
        assert all(d <= 10 for d in delays)
    
    def test_exponential_growth(self):
        """测试指数增长"""
        d0 = exponential_backoff_with_jitter(0, base_delay=1, max_delay=100)
        d1 = exponential_backoff_with_jitter(1, base_delay=1, max_delay=100)
        d2 = exponential_backoff_with_jitter(2, base_delay=1, max_delay=100)
        
        # 期望: d0 ≈ 1, d1 ≈ 2, d2 ≈ 4 (有抖动)
        assert d0 < d1 < d2
    
    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """测试退避实际等待时间"""
        start = asyncio.get_event_loop().time()
        await exponential_backoff_with_jitter(0, base_delay=0.1, max_delay=1)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert 0.05 < elapsed < 0.3  # 允许一定误差
```

---

### 3.2 集成测试

#### 3.2.1 故障注入测试
```python
# tests/test_resilience.py
import pytest
from unittest.mock import AsyncMock, patch
import aiohttp

class TestFaultInjection:
    """故障注入测试"""
    
    @pytest.mark.asyncio
    async def test_redis_unavailable(self):
        """测试Redis不可用时的降级"""
        with patch('app.core.redis_manager.get_redis') as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis unavailable")
            
            # 幂等性检查应降级处理
            result = await check_idempotency("test-key")
            
            # 应该返回未处理，不抛出异常
            assert result == (False, None)
    
    @pytest.mark.asyncio
    async def test_buff_api_429_retry(self):
        """测试BUFF API 429错误自动重试"""
        call_count = 0
        
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # 前两次返回429
                mock_response = AsyncMock()
                mock_response.status = 429
                raise aiohttp.ClientResponseError(
                    request_info=..., 
                    history=(),
                    status=429
                )
            else:
                # 第三次成功
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"code": "OK", "data": {}})
                return mock_response
        
        with patch('aiohttp.ClientSession.request', side_effect=mock_request):
            client = BuffAPI()
            result = await client._request("GET", "http://test.com")
            
            assert call_count == 3  # 重试2次后成功
    
    @pytest.mark.asyncio
    async def test_database_timeout(self):
        """测试数据库超时处理"""
        with patch('app.core.database.get_db') as mock_db:
            mock_db.side_effect = asyncio.TimeoutError("DB timeout")
            
            # 应该正确处理超时，不泄漏连接
            with pytest.raises(Exception):
                await get_orders()
```

#### 3.2.2 并发测试
```python
# tests/test_concurrency.py
import pytest
import asyncio

class TestConcurrency:
    """并发测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_orders(self):
        """测试并发下单"""
        # 创建10个并发请求
        tasks = [
            create_order({"item_id": 1, "price": 100, "quantity": 1})
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 应该只有1个成功，其余因库存不足失败
        successes = [r for r in results if isinstance(r, dict) and r.get("success")]
        failures = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        assert len(successes) == 1
        assert len(failures) == 9
    
    @pytest.mark.asyncio
    async def test_race_condition_idempotency(self):
        """测试幂等性防止竞态条件"""
        # 模拟并发重复请求
        idempotency_key = "test-race-key"
        
        async def create_with_idempotency():
            return await create_order(..., idempotency_key=idempotency_key)
        
        results = await asyncio.gather(
            create_with_idempotency(),
            create_with_idempotency(),
            create_with_idempotency(),
        )
        
        # 应该返回相同的订单ID
        order_ids = [r.get("order_id") for r in results]
        assert len(set(order_ids)) == 1  # 只有一个唯一订单
```

---

### 3.3 边界条件测试

```python
# tests/test_boundaries.py

class TestBoundaryConditions:
    """边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_price_extremes(self):
        """测试价格极值"""
        # 最低价格
        result = await execute_buy(item_id=1, max_price=0.01)
        assert result["success"] or "price" in result.get("message", "").lower()
        
        # 最高价格
        result = await execute_buy(item_id=1, max_price=100000)
        assert "balance" in result.get("message", "").lower() or result["success"]
    
    @pytest.mark.asyncio
    async def test_zero_quantity(self):
        """测试零数量"""
        with pytest.raises(ValidationError):
            await execute_buy(item_id=1, max_price=100, quantity=0)
    
    @pytest.mark.asyncio
    async def test_negative_price(self):
        """测试负价格"""
        with pytest.raises(ValidationError):
            await execute_buy(item_id=1, max_price=-10)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_search(self):
        """测试搜索特殊字符"""
        # SQL注入防护
        result = await search_items("'; DROP TABLE items;--")
        assert "error" not in result or "sql" not in result.get("error", "").lower()
        
        # XSS防护
        result = await search_items("<script>alert(1)</script>")
        assert "<script>" not in result.get("items", [])
```

---

## 四、生产环境部署最佳实践

### 4.1 容器化部署

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: ./backend
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/cs2trade
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 3

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=cs2trade
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d cs2trade"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

---

### 4.2 健康检查设计

```python
# backend/app/api/health.py
from fastapi import APIRouter
from typing import Dict, Any
import aiohttp

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """综合健康检查"""
    health = {
        "status": "healthy",
        "checks": {}
    }
    
    # 1. 数据库检查
    try:
        from app.core.database import get_db
        async with get_db() as db:
            await db.execute("SELECT 1")
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # 2. Redis检查
    try:
        from app.core.redis_manager import get_redis
        redis = await get_redis()
        await redis.ping()
        health["checks"]["redis"] = "ok"
    except Exception as e:
        health["checks"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # 3. 外部API检查
    try:
        from app.services.buff_service import get_buff_client
        buff = get_buff_client()
        # 轻量级检查
        health["checks"]["buff_api"] = "ok"
    except Exception as e:
        health["checks"]["buff_api"] = f"error: {str(e)}"
    
    return health

@router.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """就绪检查（启动完成后）"""
    return {"status": "ready"}
```

---

### 4.3 监控与告警

```yaml
# prometheus/rules.yml
groups:
  - name: cs2-trade-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "错误率超过5%"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间P95超过2秒"
      
      - alert: RedisConnectionFailure
        expr: redis_connected_clients == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis连接数为0"
      
      - alert: DatabaseConnectionPoolExhausted
        expr: sum(pg_stat_activity_count) > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "数据库连接池接近上限"
```

---

### 4.4 日志管理

```python
# backend/app/core/logging_config.py
import logging
import json
from datetime import datetime
from typing import Any

class JSONFormatter(logging.Formatter):
    """JSON格式日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log
_data)

# 配置logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": JSONFormatter},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/cs2-trade/app.log",
            "maxBytes": 104857600,  # 100MB
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}
```

---

### 4.5 安全加固

```bash
# Dockerfile 安全加固
FROM python:3.11-slim

# 创建非root用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 设置权限
RUN mkdir -p /app && chown -R appuser:appgroup /app

# 切换到非root用户
USER appuser

# 只读文件系统 (如需要)
# READONLY=true

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

---

## 五、总结与建议

### 问题优先级建议

| 优先级 | 问题 | 修复难度 | 影响范围 |
|--------|------|----------|----------|
| P1-5 | 审计日志加密 | 低 | 安全合规 |
| P1-1 | 指数退避 | 低 | 稳定性 |
| P1-4 | 幂等性Key | 低 | 正确性 |
| P1-2 | 返回格式统一 | 中 | 可维护性 |
| P1-3 | Steam健康检查 | 中 | 稳定性 |

### 可拓展性路线图

1. **短期 (本轮)**: 修复P1问题
2. **中期 (1-2轮)**: 配置热更新、插件化架构基础
3. **长期 (3-5轮)**: 多市场支持、微服务拆分

### 测试覆盖率目标

- 单元测试: 80%+
- 集成测试: 50%+
- 故障注入测试: 20+ 场景

---

*调研完成 - 21号研究员*
*2026-03-11*
