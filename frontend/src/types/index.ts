export interface User {
  id: number;
  username: string;
  email: string;
  steam_id?: string;
  balance?: number;
  is_active?: boolean;
  is_superuser?: boolean;
}

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
}

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
}

export interface Inventory {
  id: number;
  user_id: number;
  item_id: number;
  quantity: number;
}

export interface MonitorTask {
  id: number;
  name: string;
  item_name: string;
  target_price: number;
  enabled: boolean;
}

export interface DashboardStats {
  total_orders: number;
  total_profit: number;
  active_items: number;
}
