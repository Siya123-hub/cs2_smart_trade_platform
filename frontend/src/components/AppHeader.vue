<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo" @click="goHome">
        <span class="logo-icon">🎮</span>
        <span class="logo-text">CS2 Trading</span>
      </div>
    </div>
    
    <div class="header-center">
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="搜索饰品..."
          @keyup.enter="handleSearch"
        />
        <button @click="handleSearch" class="search-btn">
          <span>🔍</span>
        </button>
      </div>
    </div>
    
    <div class="header-right">
      <div class="market-status">
        <span class="status-dot" :class="{ online: marketOnline }"></span>
        <span class="status-text">{{ marketOnline ? '市场在线' : '市场离线' }}</span>
      </div>
      
      <div class="notifications" @click="showNotifications">
        <span class="notification-icon">🔔</span>
        <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
      </div>
      
      <div class="user-menu" @click="toggleUserMenu">
        <div class="avatar">{{ userInitial }}</div>
        <span class="username">{{ username }}</span>
        <span class="arrow">▼</span>
        
        <div v-if="userMenuOpen" class="dropdown-menu">
          <div class="dropdown-item" @click="goToSettings">
            <span>⚙️</span> 设置
          </div>
          <div class="dropdown-item" @click="handleLogout">
            <span>🚪</span> 退出登录
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const searchQuery = ref('')
const userMenuOpen = ref(false)
const unreadCount = ref(0)
const marketOnline = ref(true)

const username = computed(() => userStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())

const emit = defineEmits(['search', 'logout'])

const goHome = () => {
  router.push('/')
}

const handleSearch = () => {
  emit('search', searchQuery.value)
}

const showNotifications = () => {
  // TODO: 显示通知面板
}

const toggleUserMenu = () => {
  userMenuOpen.value = !userMenuOpen.value
}

const goToSettings = () => {
  userMenuOpen.value = false
  router.push('/settings')
}

const handleLogout = () => {
  userMenuOpen.value = false
  emit('logout')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  background: #1a1a2e;
  border-bottom: 1px solid #16213e;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.header-center {
  flex: 1;
  max-width: 400px;
  margin: 0 20px;
}

.search-box {
  display: flex;
  align-items: center;
  background: #16213e;
  border-radius: 8px;
  overflow: hidden;
}

.search-box input {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #fff;
  outline: none;
}

.search-box input::placeholder {
  color: #888;
}

.search-btn {
  padding: 8px 12px;
  background: #0f3460;
  border: none;
  cursor: pointer;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.market-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #888;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4444;
}

.status-dot.online {
  background: #00ff88;
}

.notifications {
  position: relative;
  cursor: pointer;
  font-size: 18px;
}

.badge {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: #ff4444;
  border-radius: 8px;
  font-size: 10px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  cursor: pointer;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #0f3460;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #fff;
}

.username {
  color: #fff;
  font-size: 14px;
}

.arrow {
  color: #888;
  font-size: 10px;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: #1a1a2e;
  border: 1px solid #16213e;
  border-radius: 8px;
  overflow: hidden;
  min-width: 150px;
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #16213e;
}
</style>
