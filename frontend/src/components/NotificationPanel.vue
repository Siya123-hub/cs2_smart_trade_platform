<template>
  <div class="notification-panel" v-if="visible">
    <div class="panel-overlay" @click="close"></div>
    <div class="panel-content">
      <div class="panel-header">
        <h3>通知中心</h3>
        <div class="header-actions">
          <el-button 
            v-if="unreadCount > 0" 
            link 
            type="primary" 
            @click="markAllRead"
          >
            全部已读
          </el-button>
          <el-button link @click="close">✕</el-button>
        </div>
      </div>
      
      <div class="panel-body" v-loading="loading">
        <div v-if="notifications.length === 0 && !loading" class="empty-state">
          <span class="empty-icon">🔔</span>
          <p>暂无通知</p>
        </div>
        
        <div v-else class="notification-list">
          <div 
            v-for="notification in notifications" 
            :key="notification.id"
            class="notification-item"
            :class="{ 
              unread: !notification.is_read,
              [`priority-${notification.priority}`]: true 
            }"
            @click="handleNotificationClick(notification)"
          >
            <div class="notification-icon">
              <span>{{ getNotificationIcon(notification.notification_type) }}</span>
            </div>
            <div class="notification-content">
              <div class="notification-title">{{ notification.title }}</div>
              <div class="notification-text">{{ notification.content }}</div>
              <div class="notification-time">{{ formatTime(notification.created_at) }}</div>
            </div>
            <div class="notification-actions">
              <el-button 
                v-if="!notification.is_read" 
                link 
                size="small" 
                @click.stop="markAsRead(notification.id)"
              >
                已读
              </el-button>
              <el-button 
                link 
                size="small" 
                type="danger"
                @click.stop="deleteNotification(notification.id)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="panel-footer" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          small
          @current-change="fetchNotifications"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getNotifications, markAsRead as apiMarkAsRead, markAllAsRead, deleteNotification as apiDeleteNotification } from '@/api/notifications'

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

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits(['close', 'update:unreadCount'])

const loading = ref(false)
const notifications = ref<Notification[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

const fetchNotifications = async () => {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const response = await getNotifications(skip, pageSize.value)
    notifications.value = response.notifications
    total.value = response.total
    emit('update:unreadCount', response.unread_count)
  } catch (error: any) {
    ElMessage.error('获取通知失败')
  } finally {
    loading.value = false
  }
}

const markAsRead = async (id: number) => {
  try {
    await apiMarkAsRead(id)
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.is_read = true
    }
    emit('update:unreadCount', unreadCount.value - 1)
  } catch (error: any) {
    ElMessage.error('标记已读失败')
  }
}

const markAllRead = async () => {
  try {
    await markAllAsRead()
    notifications.value.forEach(n => n.is_read = true)
    emit('update:unreadCount', 0)
    ElMessage.success('已全部标记为已读')
  } catch (error: any) {
    ElMessage.error('操作失败')
  }
}

const deleteNotification = async (id: number) => {
  try {
    await apiDeleteNotification(id)
    notifications.value = notifications.value.filter(n => n.id !== id)
    total.value--
    ElMessage.success('删除成功')
  } catch (error: any) {
    ElMessage.error('删除失败')
  }
}

const handleNotificationClick = (notification: Notification) => {
  if (!notification.is_read) {
    markAsRead(notification.id)
  }
  
  // 处理通知点击事件
  if (notification.data?.route) {
    // 跳转到对应页面
  }
}

const getNotificationIcon = (type: string): string => {
  const icons: Record<string, string> = {
    order: '📦',
    price: '💰',
    inventory: '🎮',
    monitor: '👁️',
    system: '⚙️',
    trade: '🔄'
  }
  return icons[type] || '🔔'
}

const formatTime = (time: string): string => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString()
}

const close = () => {
  emit('close')
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    fetchNotifications()
  }
})

onMounted(() => {
  if (props.visible) {
    fetchNotifications()
  }
})
</script>

<style scoped>
.notification-panel {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
}

.panel-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
}

.panel-content {
  position: relative;
  width: 400px;
  max-width: 100%;
  height: 100%;
  background: #fff;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.notification-list {
  display: flex;
  flex-direction: column;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f9f9f9;
}

.notification-item.unread {
  background: #f0f7ff;
}

.notification-item.unread:hover {
  background: #e6f0fa;
}

.notification-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.notification-text {
  font-size: 12px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.notification-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

/* 优先级样式 */
.priority-high {
  border-left: 3px solid #e6a23c;
}

.priority-urgent {
  border-left: 3px solid #f56c6c;
}

.panel-footer {
  padding: 12px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: center;
}

/* 响应式 */
@media (max-width: 480px) {
  .panel-content {
    width: 100%;
  }
}
</style>
