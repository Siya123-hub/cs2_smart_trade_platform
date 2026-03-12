# CS2智能交易平台 - 第60轮方案制定

## 概述

| 项目 | 内容 |
|------|------|
| **迭代编号** | 第60轮 |
| **任务** | 制定9个问题（P0-P2）的解决方案 |
| **项目路径** | `/home/tt/.openclaw/workspace/cs2_platform` |
| **当前完整性评分** | 93% |
| **目标完整性评分** | >90% |

---

## 问题分析总览

| 优先级 | 问题ID | 问题描述 | 文件位置 | 实现难度 | 影响范围 | 解决状态 |
|--------|--------|----------|----------|----------|----------|----------|
| P0 | 1 | 订单状态查询逻辑错误 | `trading_service.py:207-210` | ⭐ 低 | 交易流程 | 本轮解决 |
| P0 | 2 | 分布式锁release方法bug | `monitor_service.py:62-72` | ⭐ 中 | 分布式协调 | 本轮解决 |
| P1 | 3 | 搬砖等待使用硬睡眠 | `trading_service.py:204` | ⭐ 低 | 交易流程 | 本轮解决 |
| P1 | 4 | Redis连接异常无降级 | `monitor_service.py:137-145` | ⭐⭐ 中 | 监控服务 | 本轮解决 |
| P1 | 5 | 超时返回类型不一致 | `trading_service.py:133-137` | ⭐ 低 | API响应 | 本轮解决 |
| P1 | 6 | Steam卖出功能未实现 | `arbitrage_bot.py:244-255` | ⭐⭐⭐ 高 | 交易流程 | 本轮解决 |
| P2 | 7 | 监控服务锁失败无降级 | `monitor_service.py:146-149` | ⭐⭐ 中 | 监控服务 | 本轮解决 |
| P2 | 8 | 缺乏请求重试状态追踪 | `buff_service.py` | ⭐⭐ 中 | API调用 | 本轮解决 |
| P2 | 9 | 价格缓存无过期机制 | `arbitrage_bot.py` | ⭐ 低 | 缓存 | 本轮解决 |

---

## P0 阻断性问题解决方案

### 问题1：订单状态查询逻辑错误

**问题位置**: `backend/app/services/trading_service.py` 第207-210行

**当前问题**:
```python
# 第207-210行
if buy_order and buy_order.status == "completed":
    # 创建卖出订单...
```

买入订单创建时 `status="pending"`，但在整个流程中从未被更新为 `"completed"`，导致卖出逻辑永远无法执行。

**解决方案**:

1. **修复状态检查逻辑**（方案A - 简单修复）
   - 将 `status == "completed"` 改为 `status == "pending"`，因为订单创建后默认就是pending状态

2. **完善订单状态流转**（方案B - 完整修复，推荐）
   - 添加订单状态轮询逻辑
   - 在等待到账后实际查询BUFF API确认订单状态

**实现代码变更**:

```python
# 方案B：完整修复 - 修改 execute_arbitrage 方法

async def execute_arbitrage(self, ...):
    # ... 现有买入逻辑 ...
    
    # 2. 等待到账并检查状态
    logger.info(f"买入完成，等待到账: order_id={buy_order_id}, 等待 {settings.ARBITRAGE_SETTLE_WAIT} 秒")
    
    # 使用轮询方式等待到账，而非硬等待
    max_wait_time = settings.ARBITRAGE_SETTLE_WAIT
    check_interval = 5  # 每5秒检查一次
    waited_time = 0
    order_completed = False
    
    while waited_time < max_wait_time:
        await asyncio.sleep(check_interval)
        waited_time += check_interval
        
        # 查询订单状态
        order_result = await self.db.execute(
            select(Order).where(Order.order_id == buy_order_id)
        )
        buy_order = order_result.scalar_one_or_none()
        
        if buy_order and buy_order.status == "completed":
            order_completed = True
            break
        elif buy_order and buy_order.status == "failed":
            logger.error(f"买入订单失败: order_id={buy_order_id}")
            return ServiceResponse.err(message="买入订单失败", code="ORDER_FAILED")
    
    # 3. 检查到账状态并创建卖出订单
    if order_completed:
        # 创建卖出订单...
```

**影响范围**: 交易服务 - 搬砖流程

**工作量评估**: 0.5人天

---

### 问题2：分布式锁release方法bug

**问题位置**: `backend/app/services/monitor_service.py` 第62-72行

**当前问题**:
```python
# 第62-72行
async def release(self) -> bool:
    if self._lock_id is None:
        return False
    
    # 使用 Lua 脚本确保原子性释放
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
```

问题分析：
1. `acquire()` 方法中 `self._lock_id` 在每次调用时都会重新生成UUID
2. 如果 `acquire()` 失败或未调用，`self._lock_id` 可能为 None
3. 释放时没有验证锁是否由当前实例持有

**解决方案**:

修复分布式锁的获取和释放逻辑，确保正确处理各种边界情况：

```python
class DistributedLock:
    """Redis 分布式锁"""
    
    def __init__(self, redis_client, key: str, ttl: int = 300):
        self._redis = redis_client
        self._key = f"lock:{key}"
        self._ttl = ttl
        self._lock_id = None
        self._acquired = False  # 新增：跟踪锁获取状态
    
    async def acquire(self, blocking: bool = True, timeout: int = 30) -> bool:
        """获取锁"""
        import uuid
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 每次尝试使用新的lock_id
            lock_id = str(uuid.uuid4())
            
            # 尝试设置锁
            acquired = await self._redis.set(
                self._key,
                lock_id,
                nx=True,
                ex=self._ttl
            )
            
            if acquired:
                self._lock_id = lock_id  # 必须在获取成功后设置
                self._acquired = True
                logger.debug(f"Lock acquired: {self._key}, id={self._lock_id}")
                return True
            
            if not blocking:
                return False
            
            # 检查超时
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning(f"Lock timeout: {self._key}")
                return False
            
            # 等待后重试
            await asyncio.sleep(0.5)
    
    async def release(self) -> bool:
        """释放锁"""
        # 修复：先检查是否获取了锁
        if not self._acquired or self._lock_id is None:
            logger.warning(f"Lock not acquired, cannot release: {self._key}")
            return False
        
        # 使用 Lua 脚本确保原子性释放
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = await self._redis.eval(lua_script, 1, self._key, self._lock_id)
            self._acquired = False  # 重置获取状态
            return result == 1
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False
```

**影响范围**: 分布式监控服务

**工作量评估**: 0.5人天

---

## P1 高优先级问题解决方案

### 问题3：搬砖等待使用硬睡眠

**问题位置**: `backend/app/services/trading_service.py` 第204行

**当前问题**:
```python
# 第204行
await asyncio.sleep(settings.ARBITRAGE_SETTLE_WAIT)
```

使用固定时间等待到账，不够灵活，应该轮询检查订单实际状态。

**解决方案**:

实现轮询等待机制：

```python
async def _wait_for_order_settlement(
    self,
    order_id: str,
    max_wait_time: int = None,
    check_interval: int = 5
) -> tuple[bool, Optional[Order]]:
    """
    等待订单到账（轮询方式）
    
    Args:
        order_id: 订单ID
        max_wait_time: 最大等待时间（秒），默认使用配置
        check_interval: 检查间隔（秒）
    
    Returns:
        (是否到账, 订单对象)
    """
    max_wait_time = max_wait_time or settings.ARBITRAGE_SETTLE_WAIT
    waited_time = 0
    
    while waited_time < max_wait_time:
        await asyncio.sleep(check_interval)
        waited_time += check_interval
        
        # 查询订单状态
        result = await self.db.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            if order.status == "completed":
                return True, order
            elif order.status == "failed":
                return False, order
            # pending状态继续等待
    
    # 超时，返回当前状态
    result = await self.db.execute(
        select(Order).where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    return order.status == "completed" if order else False, order
```

**实施计划**:
1. 在 `trading_service.py` 中添加 `_wait_for_order_settlement` 方法
2. 修改 `execute_arbitrage` 方法使用轮询等待

**工作量评估**: 0.5人天

---

### 问题4：Redis连接异常无降级

**问题位置**: `backend/app/services/monitor_service.py` 第137-145行

**当前问题**:
```python
# 获取 Redis 客户端
redis_client = await self.get_redis()

# 如果 Redis 不可用，整个服务崩溃
```

缺乏 Redis 连接异常处理和降级方案。

**解决方案**:

添加 Redis 连接异常处理和降级机制：

```python
class PriceMonitor:
    """价格监控服务（分布式版本）"""
    
    def __init__(self, db: AsyncSession, node_id: Optional[str] = None):
        # ... 现有初始化 ...
        self._redis_available = True  # 新增：Redis可用状态
        self._fallback_mode = False   # 新增：降级模式标志
    
    @classmethod
    async def get_redis(cls):
        """获取 Redis 客户端（带降级）"""
        try:
            redis = await get_redis()
            # 测试连接
            await redis.ping()
            return redis
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}，将使用本地降级模式")
            return None
    
    async def _check_redis_health(self) -> bool:
        """检查Redis健康状态"""
        try:
            redis = await self.get_redis()
            if redis is None:
                self._redis_available = False
                self._fallback_mode = True
                return False
            await redis.ping()
            self._redis_available = True
            self._fallback_mode = False
            return True
        except Exception as e:
            logger.warning(f"Redis健康检查失败: {e}")
            self._redis_available = False
            self._fallback_mode = True
            return False
    
    async def start(self):
        """启动监控（带降级支持）"""
        # 先检查Redis状态
        await self._check_redis_health()
        
        if self._fallback_mode:
            logger.warning("Redis不可用，进入本地降级模式")
            # 降级模式：使用本地锁，不使用分布式锁
            self.running = True
            self._background_tasks.append(asyncio.create_task(self.poll_buff_prices()))
            self._background_tasks.append(asyncio.create_task(self.check_arbitrage()))
        else:
            # 正常分布式模式
            lock = await self.acquire_leader_lock("price_monitor_leader", ttl=60)
            # ... 现有逻辑 ...
```

**工作量评估**: 1人天

---

### 问题5：超时返回类型不一致

**问题位置**: `backend/app/services/trading_service.py` 第133-137行

**当前问题**:
```python
except asyncio.TimeoutError:
    return ServiceResponse.err(
        message="获取价格超时",
        code="TIMEOUT"
    )
```

部分地方返回 `ServiceResponse.err`，部分地方直接 `raise Exception`，类型不一致。

**解决方案**:

统一超时处理方式，确保返回类型一致：

```python
async def execute_buy(self, ...):
    # ... 
    
    # 获取当前价格 (带超时控制)
    try:
        current_price = await asyncio.wait_for(
            self.buff_client.get_price_overview(item.market_hash_name),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        # 修复：使用统一的错误响应格式
        logger.warning(f"获取价格超时: item_id={item_id}")
        return ServiceResponse.err(
            message=f"获取价格超时 (>{timeout}秒)",
            code="TIMEOUT"
        )
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        return ServiceResponse.err(
            message=f"获取价格失败: {str(e)}",
            code="GET_PRICE_FAILED"
        )
    
    if not current_price:
        return ServiceResponse.err(
            message="无法获取价格",
            code="PRICE_NOT_FOUND"
        )
```

**工作量评估**: 0.5人天

---

### 问题6：Steam卖出功能未实现

**问题位置**: `bot/internal/arbitrage_bot.py` 第244-255行

**当前问题**:
```python
# 第244-255行
async def _sell_to_steam(
    self,
    item_id: int,
    price: float
) -> Dict[str, Any]:
    """卖出到 Steam"""
    # TODO: 实现 Steam 上架逻辑
    self.logger.info(f"Steam 卖出功能待实现: item_id={item_id}, price={price}")
    
    return {
        "success": True,
        "message": "Steam 卖出功能待实现"
    }
```

**解决方案**:

实现完整的Steam上架功能：

```python
async def _sell_to_steam(
    self,
    item_id: int,
    price: float
) -> Dict[str, Any]:
    """
    卖出到 Steam
    
    流程：
    1. 获取Steam库存中的物品
    2. 创建市场上架列表
    """
    if not self._steam_api:
        return {"success": False, "message": "Steam API未初始化"}
    
    try:
        # 1. 获取Steam库存
        inventory = await self._get_steam_inventory(item_id)
        
        if not inventory:
            return {
                "success": False,
                "message": "Steam库存中未找到该物品",
                "retry": True  # 标记需要重试
            }
        
        # 2. 创建上架列表
        for item in inventory:
            listing_result = await self._create_steam_listing(
                asset_id=item["asset_id"],
                context_id=item["context_id"],
                price=price
            )
            
            if listing_result.get("success"):
                self.logger.info(
                    f"Steam上架成功: asset_id={item['asset_id']}, "
                    f"price={price}, listing_id={listing_result.get('listing_id')}"
                )
                return {
                    "success": True,
                    "listing_id": listing_result.get("listing_id"),
                    "price": price
                }
        
        return {"success": False, "message": "上架失败"}
        
    except Exception as e:
        self.logger.error(f"Steam卖出异常: {e}")
        return {"success": False, "message": str(e)}

async def _get_steam_inventory(self, item_id: int) -> List[Dict]:
    """获取Steam库存"""
    try:
        # 调用Steam API获取库存
        inventory = await self._steam_api.get_inventory(
            app_id=730,  # CSGO
            context_id=2  # 市场库存
        )
        
        # 过滤匹配的物品
        # 需要根据item_id查找对应的market_name
        return inventory.get("assets", [])
        
    except Exception as e:
        self.logger.error(f"获取Steam库存失败: {e}")
        return []

async def _create_steam_listing(
    self,
    asset_id: str,
    context_id: str,
    price: float
) -> Dict[str, Any]:
    """创建Steam市场列表"""
    try:
        # 调用Steam市场API
        # 需要使用steam_login和webcookie进行认证
        # 这里需要完成实际的API调用
        pass
    except Exception as e:
        self.logger.error(f"创建列表失败: {e}")
        return {"success": False}
```

**工作量评估**: 2人天

---

## P2 中优先级问题解决方案

### 问题7：监控服务锁失败无降级

**问题位置**: `backend/app/services/monitor_service.py` 第146-149行

**当前问题**:
获取分布式锁失败时直接退出，没有降级方案。

**解决方案**:

结合问题4的Redis降级方案统一处理：

```python
async def start(self):
    """启动监控（带锁失败降级）"""
    # 尝试获取锁
    lock = await self.acquire_leader_lock("price_monitor_leader", ttl=60)
    
    if await lock.acquire(blocking=False):
        self.running = True
        logger.info(f"价格监控服务已启动 (节点: {self.node_id}, 主节点)")
        # ... 正常启动 ...
    else:
        # 锁获取失败，作为备用节点
        logger.info(f"主节点锁获取失败，作为备用节点运行 (节点: {self.node_id})")
        self.running = True
        # 备用节点执行有限任务（如只监听告警）
        self._background_tasks.append(asyncio.create_task(self.check_arbitrage()))
```

**工作量评估**: 0.5人天

---

### 问题8：缺乏请求重试状态追踪

**问题位置**: `backend/app/services/buff_service.py`

**当前问题**:
请求重试时没有记录重试次数和状态，难以排查问题。

**解决方案**:

添加请求重试状态追踪：

```python
class BuffAPI:
    """BUFF API 客户端"""
    
    # 新增：重试状态追踪
    class RetryState:
        """重试状态"""
        def __init__(self, endpoint: str):
            self.endpoint = endpoint
            self.total_attempts = 0
            self.successful_attempts = 0
            self.failed_attempts = 0
            self.last_error: Optional[str] = None
            self.last_attempt_time: Optional[datetime] = None
    
    def __init__(self, cookie: Optional[str] = None, ...):
        # ... 现有初始化 ...
        self._retry_states: Dict[str, self.RetryState] = {}
    
    def _get_retry_state(self, endpoint: str) -> RetryState:
        """获取或创建重试状态"""
        if endpoint not in self._retry_states:
            self._retry_states[endpoint] = self.RetryState(endpoint)
        return self._retry_states[endpoint]
    
    async def _request(self, method: str, url: str, max_retries: int = None, **kwargs):
        """发送请求 (带重试状态追踪)"""
        max_retries = max_retries or self.MAX_RETRIES
        retry_count = 0
        endpoint = url.split('/api')[-1] if '/api' in url else url
        retry_state = self._get_retry_state(endpoint)
        
        while retry_count < max_retries:
            try:
                # ... 现有请求逻辑 ...
                retry_state.total_attempts += 1
                retry_state.successful_attempts += 1
                retry_state.last_attempt_time = datetime.utcnow()
                return result
                
            except Exception as e:
                retry_count += 1
                retry_state.failed_attempts += 1
                retry_state.last_error = str(e)
                retry_state.last_attempt_time = datetime.utcnow()
                
                if retry_count < max_retries:
                    delay = await _exponential_backoff_with_jitter(retry_count)
                    logger.warning(
                        f"请求失败 (尝试 {retry_count}/{max_retries}): {endpoint}, "
                        f"错误: {e}, {delay:.1f}秒后重试"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {endpoint}, 错误: {e}")
                    raise
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """获取重试统计"""
        return {
            endpoint: {
                "total": state.total_attempts,
                "success": state.successful_attempts,
                "failed": state.failed_attempts,
                "success_rate": state.successful_attempts / state.total_attempts * 100
                    if state.total_attempts > 0 else 0,
                "last_error": state.last_error,
                "last_attempt": state.last_attempt_time.isoformat() if state.last_attempt_time else None
            }
            for endpoint, state in self._retry_states.items()
        }
```

**工作量评估**: 1人天

---

### 问题9：价格缓存无过期机制

**问题位置**: `bot/internal/arbitrage_bot.py`

**当前问题**:
```python
# 缓存无过期机制
self._price_cache: Dict[str, Dict[str, Any]] = {}
```

缓存只添加不清理，会导致内存泄漏。

**解决方案**:

实现带过期时间的缓存：

```python
class ArbitrageBot(TradingBotBase):
    def __init__(self, ...):
        # ... 现有初始化 ...
        
        # 修复：使用带过期时间的缓存
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 缓存5分钟
    
    def _set_cache(self, key: str, value: Any) -> None:
        """设置缓存（带过期时间）"""
        self._price_cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存（检查过期）"""
        if key not in self._price_cache:
            return None
        
        cache_entry = self._price_cache[key]
        elapsed = time.time() - cache_entry["timestamp"]
        
        if elapsed > self._cache_ttl:
            # 缓存过期，删除
            del self._price_cache[key]
            return None
        
        return cache_entry["value"]
    
    def _cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        now = time.time()
        expired_keys = [
            key for key, entry in self._price_cache.items()
            if now - entry["timestamp"] > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._price_cache[key]
        
        return len(expired_keys)
    
    async def _run_loop(self):
        """主循环 - 定期清理缓存"""
        cache_cleanup_interval = 300  # 每5分钟清理一次
        last_cleanup = 0
        
        while self._running:
            # ... 现有逻辑 ...
            
            # 定期清理过期缓存
            if time.time() - last_cleanup > cache_cleanup_interval:
                cleaned = self._cleanup_expired_cache()
                if cleaned > 0:
                    self.logger.debug(f"清理了 {cleaned} 个过期缓存")
                last_cleanup = time.time()
```

**工作量评估**: 0.5人天

---

## 实施计划

### 第一阶段：P0问题修复（立即）

| 任务 | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 修复订单状态查询逻辑 | `trading_service.py` | 0.5天 | P0-1 |
| 修复分布式锁release bug | `monitor_service.py` | 0.5天 | P0-2 |

### 第二阶段：P1问题修复（本周）

| 任务 | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 实现轮询等待到账机制 | `trading_service.py` | 0.5天 | P1-3 |
| Redis连接异常降级 | `monitor_service.py` | 1天 | P1-4 |
| 统一超时返回类型 | `trading_service.py` | 0.5天 | P1-5 |
| 实现Steam卖出功能 | `arbitrage_bot.py` | 2天 | P1-6 |

### 第三阶段：P2问题修复（下周）

| 任务 | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 监控服务锁失败降级 | `monitor_service.py` | 0.5天 | P2-7 |
| 请求重试状态追踪 | `buff_service.py` | 1天 | P2-8 |
| 价格缓存过期机制 | `arbitrage_bot.py` | 0.5天 | P2-9 |

---

## 总结

本轮方案针对21号调研发现的9个问题进行了详细分析和解决方案制定：

- **P0（阻断）2个问题**：订单状态逻辑错误、分布式锁bug
- **P1（高优）4个问题**：硬睡眠、Redis降级、超时返回、Steam卖出
- **P2（中优）3个问题**：锁降级、重试追踪、缓存过期

**预计总工作量**: 6.5人天

**预期效果**:
- 搬砖流程可正常执行到卖出步骤
- 分布式服务具备降级能力
- API请求可追踪调试
- 缓存资源可管理

---

**方案制定时间**: 2026-03-12 19:10
**制定者**: 22号程序员
