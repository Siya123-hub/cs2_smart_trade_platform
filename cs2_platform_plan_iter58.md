# CS2 智能交易平台 - 第58轮方案

## 迭代背景
- **上一轮评分**: 93%
- **目标**: >90% 完整性

## 本轮选择解决的问题

| 优先级 | 问题 | 位置 | 解决方案 |
|--------|------|------|----------|
| P0 | 配置更新无热重载 | config.py | 实现配置文件监听和热重载 |
| P0 | 限流配置字符串化 | config.py:54 | 改为字典配置 + 解析器 |
| P1 | 等待时间硬编码 | trading_service.py:159 | 改为配置项 |
| P1 | 价格变化阈值硬编码 | monitor_service.py:145 | 改为配置项 |

---

## 方案设计

### 1. 配置热重载 (P0)

**目标**: 实现运行时配置更新，无需重启服务

**方案**:
- 使用 `watchdog` 库监听配置文件变化
- 实现配置变更回调机制
- 支持配置变更事件发布

```python
# 新增配置重载相关
class ConfigReloader:
    - watch_config_file(): 监听配置文件
    - reload(): 重新加载配置
    - subscribe(callback): 订阅配置变更
```

### 2. 限流配置解析 (P0)

**目标**: 将字符串配置转为结构化配置

**当前问题**:
```python
RATE_LIMIT_ENDPOINTS: str = """{...}"""  # JSON 字符串
```

**解决方案**:
```python
# 改为字典配置
RATE_LIMIT_ENDPOINTS: Dict = Field(default={...})

# 添加解析方法
def get_rate_limit_config() -> Dict
```

### 3. 等待时间配置化 (P1)

**目标**: 将硬编码的等待时间改为配置项

**当前**:
```python
await asyncio.sleep(10)  # line 159
```

**解决方案**:
```python
# config.py 新增
ARBITRAGE_SETTLE_WAIT: int = 10  # 搬砖买入后等待到账时间(秒)

# trading_service.py
await asyncio.sleep(settings.ARBITRAGE_SETTLE_WAIT)
```

### 4. 价格变化阈值配置化 (P1)

**目标**: 将硬编码的价格变化阈值改为配置项

**当前**:
```python
abs(new_price - item.current_price) > 0.01  # line 145
```

**解决方案**:
```python
# config.py 新增
PRICE_CHANGE_THRESHOLD: float = 0.01  # 价格变化阈值

# monitor_service.py
if item.current_price is None or abs(new_price - item.current_price) > settings.PRICE_CHANGE_THRESHOLD:
```

---

## 实现计划

### Step 1: 修改 config.py
1. 添加热重载相关配置和方法
2. 修改 RATE_LIMIT_ENDPOINTS 为字典类型
3. 添加 ARBITRAGE_SETTLE_WAIT 和 PRICE_CHANGE_THRESHOLD 配置项

### Step 2: 修改 trading_service.py
1. 将硬编码的 `asyncio.sleep(10)` 改为使用配置

### Step 3: 修改 monitor_service.py
1. 将硬编码的 `0.01` 阈值改为使用配置
2. 移除未使用的常量定义

### Step 4: 更新依赖
- 添加 `watchdog` 到 requirements.txt（如需要）

---

## 预期效果

| 指标 | 当前 | 改进后 |
|------|------|--------|
| 配置热重载 | 无 | 支持 |
| 限流配置 | 字符串 | 字典 |
| 等待时间 | 硬编码 | 可配置 |
| 价格阈值 | 硬编码 | 可配置 |

---

## 文件变更清单

- `backend/app/core/config.py` - 配置类修改
- `backend/app/services/trading_service.py` - 使用配置
- `backend/app/services/monitor_service.py` - 使用配置
