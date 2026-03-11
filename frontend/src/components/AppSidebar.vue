<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <nav class="nav-menu">
      <div 
        v-for="item in menuItems" 
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </div>
    </nav>
    
    <div class="sidebar-footer">
      <div class="collapse-btn" @click="toggleCollapse">
        <span>{{ collapsed ? '→' : '←' }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

defineProps<{
  collapsed?: boolean
}>()

const emit = defineEmits(['collapse'])

const router = useRouter()
const route = useRoute()

const currentPath = computed(() => route.path)

const menuItems = [
  { path: '/', icon: '📊', label: '仪表盘' },
  { path: '/market', icon: '🛒', label: '市场行情' },
  { path: '/inventory', icon: '🎒', label: '库存管理' },
  { path: '/orders', icon: '📋', label: '订单管理' },
  { path: '/automation', icon: '🤖', label: '自动化' },
  { path: '/stats', icon: '📈', label: '数据统计' },
]

const navigate = (path: string) => {
  router.push(path)
}

const toggleCollapse = () => {
  emit('collapse')
}
</script>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 200px;
  height: 100%;
  background: #1a1a2e;
  border-right: 1px solid #16213e;
  transition: width 0.3s ease;
}

.app-sidebar.collapsed {
  width: 60px;
}

.nav-menu {
  flex: 1;
  padding: 20px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #16213e;
  color: #fff;
}

.nav-item.active {
  background: #0f3460;
  color: #00d4ff;
  border-left: 3px solid #00d4ff;
}

.nav-icon {
  font-size: 18px;
  min-width: 24px;
  text-align: center;
}

.nav-label {
  font-size: 14px;
  white-space: nowrap;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #16213e;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 8px;
  background: #16213e;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: background 0.2s;
}

.collapse-btn:hover {
  background: #0f3460;
  color: #fff;
}
</style>
