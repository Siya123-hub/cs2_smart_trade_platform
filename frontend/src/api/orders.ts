// 订单 API
import { request } from './index'

export interface Order {
  id: number
  user_id: number
  item_id: number
  side: 'buy' | 'sell'
  price: number
  quantity: number
  status: string
  source: string
  created_at: string
  updated_at: string
}

export interface OrderListResponse {
  orders: Order[]
  total: number
  page: number
  page_size: number
}

export interface CreateOrderData {
  item_id: number
  side: 'buy' | 'sell'
  price: number
  quantity: number
}

export const ordersApi = {
  // 获取订单列表
  getList: (params?: {
    page?: number
    page_size?: number
    status?: string
    side?: string
    source?: string
  }) => request.get<OrderListResponse>('/orders/', { params }),
  
  // 获取订单详情
  getById: (id: number) => request.get<Order>(`/orders/${id}`),
  
  // 创建订单
  create: (data: CreateOrderData) => request.post<Order>('/orders/', data),
  
  // 取消订单
  cancel: (id: number) => request.post(`/orders/${id}/cancel`),
  
  // 获取订单统计
  getStatistics: () => request.get('/orders/statistics')
}

export default ordersApi
