// 饰品 API
import { request } from './index'

export interface Item {
  id: number
  name: string
  name_cn: string
  market_hash_name: string
  category: string
  rarity: string
  exterior: string
  current_price: number
  steam_lowest_price: number
  volume_24h: number
  price_change_percent: number
}

export interface ItemListResponse {
  items: Item[]
  total: number
  page: number
  page_size: number
}

export interface PriceHistory {
  id: number
  item_id: number
  source: string
  price: number
  recorded_at: string
}

export const itemsApi = {
  // 获取饰品列表
  getList: (params?: {
    page?: number
    page_size?: number
    category?: string
    rarity?: string
    exterior?: string
    min_price?: number
    max_price?: number
    sort_by?: string
    sort_order?: string
  }) => request.get<ItemListResponse>('/items/', { params }),
  
  // 搜索饰品
  search: (keyword: string, limit: number = 20) => 
    request.get('/items/search', { params: { keyword, limit } }),
  
  // 获取饰品详情
  getById: (id: number) => request.get<Item>(`/items/${id}`),
  
  // 获取价格历史
  getPriceHistory: (id: number, params?: { source?: string; days?: number }) =>
    request.get(`/items/${id}/price`, { params }),
  
  // 获取价格概览
  getPriceOverview: (id: number) => request.get(`/items/${id}/overview`)
}

export default itemsApi
