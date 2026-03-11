// 统计 API
import { request } from './index'

export interface DashboardStats {
  total_balance: number
  total_profit: number
  active_orders: number
  completed_orders: number
  inventory_value: number
}

export interface TradingStats {
  buy_count: number
  sell_count: number
  buy_volume: number
  sell_volume: number
  profit: number
}

export interface ProfitStats {
  total_profit: number
  daily_profit: number
  weekly_profit: number
  monthly_profit: number
}

export const statsApi = {
  // 获取仪表盘统计
  getDashboard: () => request.get<DashboardStats>('/stats/dashboard'),
  
  // 获取交易统计
  getTrading: (params?: { days?: number }) =>
    request.get<TradingStats>('/stats/trading', { params }),
  
  // 获取利润统计
  getProfit: (params?: { days?: number }) =>
    request.get<ProfitStats>('/stats/profit', { params }),
  
  // 获取订单统计
  getOrders: () => request.get('/stats/orders'),
  
  // 获取交易量统计
  getVolume: (params?: { days?: number }) =>
    request.get('/stats/volume', { params }),
  
  // 获取搬砖统计
  getArbitrage: (params?: { days?: number }) =>
    request.get('/stats/arbitrage', { params }),
  
  // 获取趋势统计
  getTrend: (params?: { days?: number }) =>
    request.get('/stats/trend', { params })
}

export default statsApi
