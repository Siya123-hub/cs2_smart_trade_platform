// 库存 API
import { request } from './index'

export interface InventoryItem {
  id: number
  bot_id: number
  item_id: number
  asset_id: string
  context_id: number
  instance_id: number
  amount: number
  price: number
  is_locked: boolean
  created_at: string
}

export interface InventoryListResponse {
  items: InventoryItem[]
  total: number
}

export interface InventorySummary {
  total_items: number
  total_value: number
  bot_count: number
}

export const inventoryApi = {
  // 获取库存列表
  getList: (params?: { bot_id?: number; page?: number; page_size?: number }) =>
    request.get<InventoryListResponse>('/inventory/', { params }),
  
  // 获取机器人库存
  getByBot: (botId: number) =>
    request.get(`/inventory/bot/${botId}`),
  
  // 获取库存详情
  getById: (id: number) => request.get<InventoryItem>(`/inventory/${id}`),
  
  // 获取库存摘要
  getSummary: () => request.get<InventorySummary>('/inventory/summary'),
  
  // 刷新库存
  refresh: (botId: number) => request.post(`/inventory/bot/${botId}/refresh`),
  
  // 获取库存估值
  getValuation: () => request.get('/inventory/valuation')
}

export default inventoryApi
