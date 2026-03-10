/**
 * API 客户端
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const apiClient: AxiosInstance = axios.create({
  baseURL: `${baseURL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      
      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        window.location.href = '/login'
      } else if (status === 403) {
        ElMessage.error(data.detail || '没有权限')
      } else if (status === 404) {
        ElMessage.error(data.detail || '资源不存在')
      } else if (status >= 500) {
        ElMessage.error('服务器错误')
      } else {
        ElMessage.error(data.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络错误')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient

// ============ API 接口 ============

// 认证
export const authApi = {
  login: (username: string, password: string) => 
    apiClient.post('/auth/login', null, { params: { username, password } }),
  
  register: (data: { username: string; email: string; password: string }) =>
    apiClient.post('/auth/register', data),
  
  logout: () => apiClient.post('/auth/logout'),
  
  getCurrentUser: () => apiClient.get('/auth/me'),
  
  updateUser: (data: any) => apiClient.put('/auth/me', data),
}

// 饰品
export const itemsApi = {
  list: (params: any) => apiClient.get('/items', { params }),
  
  search: (keyword: string) => apiClient.get('/items/search', { params: { keyword } }),
  
  get: (id: number) => apiClient.get(`/items/${id}`),
  
  getPriceHistory: (id: number, params: { source?: string; days?: number }) => 
    apiClient.get(`/items/${id}/price`, { params }),
  
  getOverview: (id: number) => apiClient.get(`/items/${id}/overview`),
}

// 订单
export const ordersApi = {
  list: (params: any) => apiClient.get('/orders', { params }),
  
  create: (data: any) => apiClient.post('/orders', data),
  
  get: (id: string) => apiClient.get(`/orders/${id}`),
  
  cancel: (id: string) => apiClient.delete(`/orders/${id}`),
}

// 库存
export const inventoryApi = {
  list: (params: any) => apiClient.get('/inventory', { params }),
  
  listItem: (id: number) => apiClient.get(`/inventory/${id}`),
  
  listOnMarket: (id: number, data: { price: number }) => 
    apiClient.post(`/inventory/${id}/list`, data),
  
  unlist: (id: number) => apiClient.post(`/inventory/${id}/unlist`),
}

// 监控
export const monitorsApi = {
  list: () => apiClient.get('/monitors'),
  
  create: (data: any) => apiClient.post('/monitors', data),
  
  update: (id: number, data: any) => apiClient.put(`/monitors/${id}`, data),
  
  delete: (id: number) => apiClient.delete(`/monitors/${id}`),
  
  getLogs: (id: number) => apiClient.get(`/monitors/${id}/logs`),
}

// 机器人
export const botsApi = {
  list: () => apiClient.get('/bots'),
  
  create: (data: any) => apiClient.post('/bots', data),
  
  update: (id: number, data: any) => apiClient.put(`/bots/${id}`, data),
  
  delete: (id: number) => apiClient.delete(`/bots/${id}`),
  
  login: (id: number) => apiClient.post(`/bots/${id}/login`),
  
  trade: (id: number, data: any) => apiClient.post(`/bots/${id}/trade`, data),
}

// 统计
export const statsApi = {
  dashboard: () => apiClient.get('/stats/dashboard'),
  
  profit: (params: any) => apiClient.get('/stats/profit', { params }),
  
  tradeVolume: (params: any) => apiClient.get('/stats/trade-volume', { params }),
}
