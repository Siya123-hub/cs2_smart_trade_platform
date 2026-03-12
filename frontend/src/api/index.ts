// API 统一配置
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import axiosRetry from 'axios-retry'
import { useUserStore } from '@/stores/user'

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 配置 axios-retry 重试机制
axiosRetry(apiClient, {
  retries: 3,                          // 重试次数
  retryDelay: (retryCount) => {
    return retryCount * 1000           // 重试延迟：1s, 2s, 3s
  },
  retryCondition: (error) => {
    // 仅在这些错误时重试
    return (
      error.code === 'ECONNABORTED' ||                 // 请求超时
      error.response?.status === 429 ||                // 请求过于频繁
      error.response?.status === 500 ||                // 服务器内部错误
      error.response?.status === 502 ||                // 网关错误
      error.response?.status === 503 ||                // 服务不可用
      error.response?.status === 504                    // 网关超时
    )
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const userStore = useUserStore()
    const status = error.response?.status
    
    if (status === 401) {
      // Token 过期，清除并跳转登录
      userStore.logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }
    
    // 错误信息处理
    let errorMessage = '请求失败'
    
    if (status === 400) {
      // 业务逻辑错误 - 尝试从响应中获取详细错误信息
      const detail = error.response?.data?.detail
      if (Array.isArray(detail)) {
        // FastAPI validation error 格式
        errorMessage = detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ')
      } else if (typeof detail === 'string') {
        errorMessage = detail
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else {
        errorMessage = '请求参数错误'
      }
    } else if (status === 403) {
      errorMessage = '没有权限执行此操作'
    } else if (status === 404) {
      errorMessage = '请求的资源不存在'
    } else if (status === 429) {
      errorMessage = '请求过于频繁，请稍后重试'
    } else if (status === 500) {
      errorMessage = '服务器内部错误'
    } else if (status === 502) {
      errorMessage = '网关错误'
    } else if (status === 503) {
      errorMessage = '服务暂时不可用'
    } else if (status === 504) {
      errorMessage = '网关超时，请稍后重试'
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = '请求超时'
    } else if (!error.response) {
      errorMessage = '网络连接失败'
    }
    
    // 将错误信息附加到 error 对象
    error.userMessage = errorMessage
    
    return Promise.reject(error)
  }
)

// 通用请求方法
export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return apiClient.get(url, config)
  },
  
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return apiClient.post(url, data, config)
  },
  
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return apiClient.put(url, data, config)
  },
  
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return apiClient.delete(url, config)
  },
  
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return apiClient.patch(url, data, config)
  }
}

export default apiClient
