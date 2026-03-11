# 调研报告 - 第28轮

## 调研时间
2026-03-11 15:45

---

## 一、上轮问题分析

### 1.1 P0: Python 3.8 兼容性问题 ✅ 已识别（待修复）

**问题描述:**
- `market.py` 使用了 `list[MyListingItem]` Python 3.9+ 语法
- 会导致 Python 3.8 环境下应用无法启动

**当前状态:** 尚未修复，需要在代码层面确认

---

### 1.2 P1: 挂单功能测试缺失 ✅ 已识别

**问题描述:**
- 缺少 `tests/api/test_market.py`
- 挂单相关功能没有单元测试覆盖

**当前状态:** 待实现

---

### 1.3 P1: 交易限额未实施 ✅ 已识别

**问题描述:**
- `config.py` 定义了 `MAX_SINGLE_TRADE: float = 10000`
- 但 `trading_service.py` 未实际使用

**当前状态:** 待实现

---

## 二、本轮深度分析 - 重点改进点

### 2.1 鲁棒性改进（目标: 86% → 90%）

#### 问题1: 前端统一错误处理机制缺失

**位置:** `frontend/src/api/index.ts`

**问题描述:**
```typescript
// 当前响应拦截器只处理了 401 错误
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      userStore.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

**影响:**
- ❌ 500/502/503 等服务器错误没有统一提示
- ❌ 网络超时没有友好提示
- ❌ 各组件需要重复编写错误处理逻辑
- ❌ 用户体验差，遇到问题不知道发生了什么

**改进建议:**
```typescript
// 增强响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const messages = {
      400: '请求参数有误',
      401: '登录已过期，请重新登录',
      403: '没有权限执行此操作',
      404: '请求的资源不存在',
      429: '请求过于频繁，请稍后再试',
      500: '服务器内部错误',
      502: '服务暂时不可用',
      503: '服务暂时不可用',
      NETWORK_ERROR: '网络连接失败，请检查网络'
    }
    
    const message = status ? messages[status] || '操作失败' : 
                    error.code === 'ECONNABORTED' ? '请求超时' : 
                    '网络连接失败'
    
    ElMessage.error(message)
    return Promise.reject(error)
  }
)
```

**优先级:** P0（直接影响用户体验）

---

#### 问题2: 关键业务操作缺少确认机制

**位置:** `frontend/src/views/`

**问题描述:**
- 大额购买没有二次确认
- 批量操作没有风险提示
- 取消订单没有确认对话框

**影响:**
- ❌ 用户误操作风险高
- ❌ 缺乏关键操作的谨慎性
- ❌ 不符合企业级应用规范

**改进建议:**
```typescript
// 使用 Element Plus 的确认对话框
const handleBuy = async (item: MarketItem) => {
  if (item.current_price > 1000) {
    try {
      await ElMessageBox.confirm(
        `即将花费 ¥${item.current_price} 购买 ${item.name}，是否确认？`,
        '大额购买确认',
        {
          confirmButtonText: '确认购买',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
    } catch {
      return // 用户取消
    }
  }
  // 执行购买逻辑
}
```

**优先级:** P1（用户体验重要改进）

---

#### 问题3: 交易限额未实际执行

**位置:** `backend/app/services/trading_service.py`

**问题描述:**
```python
# config.py 中定义了
MAX_SINGLE_TRADE: float = 10000  # 单笔最大交易金额

# 但 trading_service.py 的 execute_buy 方法未使用
async def execute_buy(self, item_id: int, max_price: float, quantity: int = 1, ...):
    # 缺少金额校验
    # 如果 price * quantity > MAX_SINGLE_TRADE 应该拒绝
```

**影响:**
- ❌ 配置形同虚设
- ❌ 可能导致超出预期的交易损失
- ❌ 鲁棒性评分受影响

**改进建议:**
```python
async def execute_buy(self, item_id: int, max_price: float, quantity: int = 1, ...):
    # ... 现有验证 ...
    
    # 新增：交易金额上限检查
    total_amount = price * quantity
    if total_amount > settings.MAX_SINGLE_TRADE:
        return ServiceResponse.err(
            message=f"单笔交易金额 {total_amount} 超过上限 {settings.MAX_SINGLE_TRADE}",
            code="EXCEED_MAX_TRADE"
        )
```

**优先级:** P0（安全相关）

---

### 2.2 用户体验改进（目标: 85% → 90%）

#### 问题4: 缺乏实时数据推送（WebSocket）

**位置:** 全局

**问题描述:**
- 当前使用轮询获取最新数据
- 价格变动、订单状态更新延迟
- 用户需要手动刷新页面

**影响:**
- ❌ 实时性差，搬砖机会稍纵即逝
- ❌ 用户体验差，需要频繁手动刷新
- ❌ 增加不必要的API请求

**改进建议:**
```python
# 后端：实现 WebSocket 端点
from fastapi import WebSocket

@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 推送价格变动、订单状态等
            await websocket.send_json({
                "type": "price_update",
                "data": {...}
            })
            await asyncio.sleep(1)
    except Exception:
        pass
```

```typescript
// 前端：WebSocket 客户端
const ws = new WebSocket(`ws://${location.host}/ws/notifications`)
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'price_update') {
    // 更新 store 中的价格
    marketStore.updatePrice(data.data)
  }
}
```

**优先级:** P1（用户体验重要改进）

---

#### 问题5: 前端加载状态和骨架屏缺失

**位置:** `frontend/src/views/`

**问题描述:**
- 大部分视图没有加载骨架屏
- 数据加载时页面会闪烁或空白
- 没有优雅的过渡动画

**影响:**
- ❌ 加载时用户体验差
- ❌ 感觉应用反应慢

**改进建议:**
```vue
<template>
  <!-- 使用 Element Plus 的 Skeleton -->
  <el-skeleton :rows="5" animated v-if="loading">
    <template #template>
      <el-skeleton-item variant="image" style="width: 200px; height: 200px" />
      <el-skeleton-item variant="h3" style="width: 30%" />
      <el-skeleton-item variant="text" style="margin-right: 16px" />
    </template>
  </el-skeleton>
  
  <div v-else>
    <!-- 实际内容 -->
  </div>
</template>
```

**优先级:** P2（改进建议）

---

#### 问题6: 缺乏分布式追踪

**位置:** 全局

**问题描述:**
- 当前没有集成 OpenTelemetry
- 跨服务问题定位困难
- 无法追踪完整请求链路

**影响:**
- ❌ 问题排查效率低
- ❌ 难以分析性能瓶颈
- ❌ 可观测性不足

**改进建议:**
```python
# 安装依赖
# pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 初始化
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# 使用
tracer = trace.get_tracer(__name__)

@app.get("/api/v1/items")
async def get_items():
    with tracer.start_as_current_span("get_items") as span:
        span.set_attribute("http.method", "GET")
        # 业务逻辑
```

**优先级:** P2（可拓展性改进）

---

### 2.3 可拓展性改进（目标: 91% → 93%）

#### 问题7: v2 API 目录结构不规范

**位置:** `backend/app/api/v2/`

**问题描述:**
- `v2/endpoints/` 目录为空
- 端点定义全部在 `v2/__init__.py` 中
- 与 v1 目录结构不一致

**影响:**
- ❌ 代码组织不规范
- ❌ 后续维护困难
- ❌ 可拓展性评分受影响

**改进建议:**
将 `v2/__init__.py` 中的端点拆分到 `v2/endpoints/` 下的独立文件：
```
v2/
├── __init__.py      # 路由汇总
├── endpoints/
│   ├── __init__.py
│   ├── items.py     # 增强版饰品端点
│   ├── orders.py    # 增强版订单端点
│   └── stats.py     # 实时统计端点
```

**优先级:** P2（代码规范）

---

## 三、改进优先级排序

### 3.1 P0 - 立即修复

| 问题 | 当前影响 | 改进后收益 | 预计评分提升 |
|------|----------|------------|--------------|
| Python 3.8 兼容性 | 阻塞启动 | 应用可正常运行 | +1% |
| 交易限额未实施 | 安全风险 | 符合配置预期 | +1% |
| 前端统一错误处理 | 用户体验差 | 错误提示友好 | +2% |

### 3.2 P1 - 本轮优化

| 问题 | 当前影响 | 改进后收益 | 预计评分提升 |
|------|----------|------------|--------------|
| 交易确认机制 | 误操作风险 | 操作更谨慎 | +1% |
| WebSocket 实时推送 | 数据延迟 | 实时性好 | +2% |

### 3.3 P2 - 下轮优化

| 问题 | 当前影响 | 改进后收益 | 预计评分提升 |
|------|----------|------------|--------------|
| 骨架屏加载 | 体验一般 | 加载更平滑 | +0.5% |
| 分布式追踪 | 排查困难 | 可观测性好 | +0.5% |
| v2 目录结构 | 代码混乱 | 规范易维护 | +0.5% |

---

## 四、预估评分

### 4.1 当前评分
- 功能完整性: 96%
- 鲁棒性: 86%
- 可拓展性: 91%
- 用户体验: 85%
- **综合评分: 93%**

### 4.2 修复后预估
- 功能完整性: 96% (不变)
- 鲁棒性: 88% (+2%)
- 可拓展性: 91.5% (+0.5%)
- 用户体验: 88% (+3%)
- **综合评分: 95%** ✅

---

## 五、结论

### 5.1 关键发现

**鲁棒性问题（当前86%）：**
1. 前端缺少统一错误处理机制 - 影响最大
2. 交易限额配置未实际执行 - 安全风险
3. 测试覆盖不完整

**用户体验问题（当前85%）：**
1. 缺乏WebSocket实时推送 - 核心功能差距
2. 缺少操作确认机制 - 安全性不足
3. 加载状态不够优雅

**可拓展性问题（当前91%）：**
1. v2目录结构不规范
2. 缺乏分布式追踪

### 5.2 优先改进方向

本轮建议优先解决：
1. **P0: Python 3.8 兼容性** - 阻塞性问题
2. **P0: 前端统一错误处理** - 提升用户体验立竿见影
3. **P0: 交易限额实施** - 安全相关
4. **P1: WebSocket 实时推送** - 核心功能增强
5. **P1: 交易确认机制** - 用户体验重要改进

### 5.3 预估效果

全部实施后预计达到：
- **综合评分: 95%** ✅ 达成目标

---

## 调研人
21号研究员

## 调研时间
2026-03-11 15:45
