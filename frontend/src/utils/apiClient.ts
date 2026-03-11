/**
 * API 客户端 - 统一错误处理
 * 提供更完善的错误处理和类型定义
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'

// 错误类型定义
export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
}

export interface ApiResponse<T = any> {
  data: T
  message?: string
  code?: number
}

// 错误码映射
const ERROR_CODES: Record<number, string> = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '没有操作权限',
  404: '请求的资源不存在',
  408: '请求超时',
  422: '数据验证失败',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂时不可用',
  504: '网关超时',
}

// 网络错误
const NETWORK_ERRORS: Record<string, string> = {
  ECONNABORTED: '请求超时，请稍后重试',
  ERR_NETWORK: '网络连接失败',
  ERR_CONNECTION_REFUSED: '无法连接到服务器',
}

/**
 * 创建 API 客户端实例
 */
export const createApiClient = (baseURL?: string): AxiosInstance => {
  const client = axios.create({
    baseURL: baseURL || import.meta.env.VITE_API_BASE_URL || '/api/v1',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  // 请求拦截器
  client.interceptors.request.use(
    (config) => {
      // 添加 Token
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      
      // 添加时间戳防止缓存
      if (config.method === 'get') {
        config.params = {
          ...config.params,
          _t: Date.now()
        }
      }
      
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )
  
  // 响应拦截器
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      return response
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }
      
      // 处理 401 错误 - Token 过期
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true
        
        // 尝试刷新 Token
        try {
          const refreshToken = localStorage.getItem('refresh_token')
          if (refreshToken) {
            const response = await axios.post(
              `${client.defaults.baseURL}/auth/refresh`,
              { refresh_token: refreshToken }
            )
            
            if (response.data.access_token) {
              localStorage.setItem('token', response.data.access_token)
              localStorage.setItem('refresh_token', response.data.refresh_token)
              
              // 重新发送原始请求
              originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
              return client(originalRequest)
            }
          }
        } catch (refreshError) {
          // 刷新失败，清除 Token 并跳转登录
          localStorage.removeItem('token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
      
      // 处理其他错误
      handleApiError(error)
      
      return Promise.reject(error)
    }
  )
  
  return client
}

/**
 * 处理 API 错误
 */
export const handleApiError = (error: AxiosError): void => {
  const status = error.response?.status
  const data = error.response?.data as any
  
  // 优先使用后端返回的错误信息
  let message = data?.detail || data?.message || data?.error
  
  // 如果没有后端错误信息，使用预定义的错误消息
  if (!message) {
    if (status) {
      message = ERROR_CODES[status]
    } else if (error.code) {
      message = NETWORK_ERRORS[error.code] || '网络错误'
    }
  }
  
  // 显示错误提示
  if (message) {
    // 根据错误类型选择不同的提示方式
    if (status === 401 || status === 403) {
      ElMessage.error(message)
    } else if (status && status >= 500) {
      ElNotification.error({
        title: '服务器错误',
        message: message,
        duration: 5000
      })
    } else {
      ElMessage.warning(message)
    }
  }
}

/**
 * 通用请求方法
 */
export const apiClient = createApiClient()

/**
 * GET 请求
 */
export const get = async <T = any>(
  url: string,
  params?: Record<string, any>,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await apiClient.get<T>(url, { ...config, params })
  return response.data
}

/**
 * POST 请求
 */
export const post = async <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await apiClient.post<T>(url, data, config)
  return response.data
}

/**
 * PUT 请求
 */
export const put = async <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await apiClient.put<T>(url, data, config)
  return response.data
}

/**
 * DELETE 请求
 */
export const del = async <T = any>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await apiClient.delete<T>(url, config)
  return response.data
}

/**
 * PATCH 请求
 */
export const patch = async <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await apiClient.patch<T>(url, data, config)
  return response.data
}

export default {
  createApiClient,
  handleApiError,
  get,
  post,
  put,
  delete: del,
  patch
}
