// 通知 API
import { request } from './index'

interface Notification {
  id: number
  user_id: number
  notification_type: string
  priority: string
  status: string
  title: string
  content: string
  data: Record<string, any> | null
  is_read: boolean
  created_at: string
  read_at: string | null
}

interface NotificationListResponse {
  notifications: Notification[]
  total: number
  unread_count: number
  skip: number
  limit: number
}

const BASE_URL = '/v2/notifications'

/**
 * 获取通知列表
 */
export const getNotifications = async (skip = 0, limit = 20): Promise<NotificationListResponse> => {
  const response = await request.get<NotificationListResponse>(`${BASE_URL}/?skip=${skip}&limit=${limit}`)
  return response.data
}

/**
 * 获取未读通知数量
 */
export const getUnreadCount = async (): Promise<{ unread_count: number }> => {
  const response = await request.get<{ unread_count: number }>(`${BASE_URL}/unread-count`)
  return response.data
}

/**
 * 获取单个通知详情
 */
export const getNotification = async (id: number): Promise<Notification> => {
  const response = await request.get<Notification>(`${BASE_URL}/${id}`)
  return response.data
}

/**
 * 标记通知为已读
 */
export const markAsRead = async (id: number): Promise<void> => {
  await request.put<void>(`${BASE_URL}/${id}/read`)
}

/**
 * 标记所有通知为已读
 */
export const markAllAsRead = async (): Promise<void> => {
  await request.put<void>(`${BASE_URL}/read-all`)
}

/**
 * 删除单个通知
 */
export const deleteNotification = async (id: number): Promise<void> => {
  await request.delete<void>(`${BASE_URL}/${id}`)
}

/**
 * 清空通知
 * @param readOnly 是否只删除已读通知
 */
export const clearNotifications = async (readOnly = true): Promise<void> => {
  await request.delete<void>(`${BASE_URL}/?read_only=${readOnly}`)
}
