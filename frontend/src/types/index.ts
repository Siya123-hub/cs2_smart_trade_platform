// 用户相关类型
export interface User {
  id: number;
  username: string;
  email: string;
  steam_id?: string;
  balance?: number;
  is_active?: boolean;
  is_superuser?: string;
  created_at?: string;
  avatar_url?: string;
}

// 认证相关类型
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

// 饰品相关类型
export interface Item {
  id: number;
  market_hash_name: string;
  app_id: number;
  name: string;
  name_cn?: string;
  rarity?: string;
  exterior?: string;
  category?: string;
  quality?: string;
  current_price?: number;
  lowest_price?: number;
  highest_price?: number;
  volume_24h?: number;
  price_change_percent?: number;
  steam_lowest_price?: number;
  image_url?: string;
}

export interface ItemListParams {
  page?: number;
  page_size?: number;
  category?: string;
  rarity?: string;
  exterior?: string;
  min_price?: number;
  max_price?: number;
  sort_by?: string;
  sort_order?: string;
}

export interface ItemListResponse {
  items: Item[];
  total: number;
  page: number;
  page_size: number;
}

export interface PriceHistory {
  id: number;
  item_id: number;
  source: string;
  price: number;
  recorded_at: string;
}

export interface PriceOverview {
  item_id: number;
  market_hash_name: string;
  buff_price: number;
  steam_price: number;
  arbitrage_profit: number;
  arbitrage_percent: number;
  volume_24h: number;
  price_trend: 'up' | 'down' | 'stable';
}

// 订单相关类型
export interface Order {
  id: number;
  order_id?: string;
  user_id: number;
  item_id: number;
  side: 'buy' | 'sell';
  price: number;
  quantity?: number;
  status: string;
  source: string;
  created_at?: string;
  updated_at?: string;
  item?: Item;
}

export interface OrderCreate {
  item_id: number;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
}

export interface OrderListParams {
  page?: number;
  page_size?: number;
  status?: string;
  side?: string;
  source?: string;
}

export interface OrderListResponse {
  orders: Order[];
  total: number;
  page: number;
  page_size: number;
}

// 市场页面专用类型（包含计算字段）
export interface MarketItem extends Item {
  image?: string;
  buff_price?: number;
  steam_price?: number;
  profit?: number;
  profit_rate?: number;
}

// 库存相关类型
export interface Inventory {
  id: number;
  user_id: number;
  item_id: number;
  quantity: number;
  bot_id?: number;
  asset_id?: string;
}

export interface InventoryItem {
  id: number;
  bot_id: number;
  item_id: number;
  asset_id: string;
  context_id: number;
  instance_id: number;
  amount: number;
  price: number;
  is_locked: boolean;
  created_at?: string;
  item?: Item;
}

export interface InventorySummary {
  total_items: number;
  total_value: number;
  bot_count: number;
}

// 监控任务相关类型
export interface MonitorTask {
  id: number;
  name: string;
  item_name: string;
  target_price: number;
  enabled: boolean;
  condition?: 'above' | 'below';
  notify_enabled?: boolean;
  created_at?: string;
}

export interface MonitorTaskCreate {
  name: string;
  item_name: string;
  target_price: number;
  condition?: 'above' | 'below';
  enabled?: boolean;
}

// 统计相关类型
export interface DashboardStats {
  total_orders: number;
  total_profit: number;
  active_items: number;
  balance?: number;
  inventory_value?: number;
  pending_orders?: number;
  completed_orders?: number;
}

export interface TradingStats {
  buy_count: number;
  sell_count: number;
  buy_volume: number;
  sell_volume: number;
  profit: number;
}

export interface ProfitStats {
  total_profit: number;
  daily_profit: number;
  weekly_profit: number;
  monthly_profit: number;
}

// 机器人相关类型
export interface Bot {
  id: number;
  name: string;
  steam_id: string;
  username: string;
  status: 'online' | 'offline' | 'busy';
  inventory_value?: number;
  items_count?: number;
  last_update?: string;
}

// 自动化相关类型
export interface ArbitrageRule {
  id: number;
  name: string;
  buy_from: string;
  sell_to: string;
  min_profit_percent: number;
  max_price: number;
  enabled: boolean;
}

export interface ArbitrageRuleCreate {
  name: string;
  buy_from: string;
  sell_to: string;
  min_profit_percent: number;
  max_price: number;
  enabled?: boolean;
}

// API 响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  code?: string;
}

export interface ApiError {
  status: string;
  code: string;
  message: string;
  errors?: Array<{
    code: string;
    message: string;
    field?: string;
  }>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 健康检查类型
export interface HealthCheckResponse {
  status: string;
  system?: {
    platform: string;
    python_version: string;
  };
  dependencies?: {
    sqlalchemy: string;
    redis: string;
    aiohttp: string;
  };
}

export interface ReadinessCheckResponse {
  status: string;
  checks: Record<string, string>;
}

// 通用类型
export type SortOrder = 'asc' | 'desc';

export interface SortParams {
  sort_by: string;
  sort_order: SortOrder;
}

export interface FilterParams {
  [key: string]: string | number | boolean | undefined;
}
