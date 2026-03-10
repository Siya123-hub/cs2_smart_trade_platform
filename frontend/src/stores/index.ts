/**
 * 用户 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, itemsApi, ordersApi, inventoryApi, monitorsApi, statsApi } from '@/utils/api'
import type { User, Item, Order, Inventory, MonitorTask, DashboardStats } from '@/types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  
  async function login(username: string, password: string) {
    const response: any = await authApi.login(username, password)
    token.value = response.access_token
    localStorage.setItem('token', response.access_token)
    await fetchCurrentUser()
  }
  
  async function fetchCurrentUser() {
    try {
      user.value = await authApi.getCurrentUser()
    } catch (error) {
      logout()
    }
  }
  
  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }
  
  return {
    user,
    token,
    isLoggedIn,
    login,
    fetchCurrentUser,
    logout,
  }
})

// 饰品 Store
export const useItemsStore = defineStore('items', () => {
  const items = ref<Item[]>([])
  const currentItem = ref<Item | null>(null)
  const total = ref(0)
  const loading = ref(false)
  
  async function fetchItems(params: any = {}) {
    loading.value = true
    try {
      const response: any = await itemsApi.list(params)
      items.value = response.items
      total.value = response.total
    } finally {
      loading.value = false
    }
  }
  
  async function searchItems(keyword: string) {
    const response: any = await itemsApi.search(keyword)
    return response.items
  }
  
  async function getItem(id: number) {
    currentItem.value = await itemsApi.get(id)
    return currentItem.value
  }
  
  return {
    items,
    currentItem,
    total,
    loading,
    fetchItems,
    searchItems,
    getItem,
  }
})

// 订单 Store
export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const total = ref(0)
  const loading = ref(false)
  
  async function fetchOrders(params: any = {}) {
    loading.value = true
    try {
      const response: any = await ordersApi.list(params)
      orders.value = response.orders
      total.value = response.total
    } finally {
      loading.value = false
    }
  }
  
  async function createOrder(data: any) {
    return await ordersApi.create(data)
  }
  
  async function cancelOrder(orderId: string) {
    await ordersApi.cancel(orderId)
    await fetchOrders()
  }
  
  return {
    orders,
    total,
    loading,
    fetchOrders,
    createOrder,
    cancelOrder,
  }
})

// 库存 Store
export const useInventoryStore = defineStore('inventory', () => {
  const inventory = ref<Inventory[]>([])
  const total = ref(0)
  const loading = ref(false)
  
  async function fetchInventory(params: any = {}) {
    loading.value = true
    try {
      const response: any = await inventoryApi.list(params)
      inventory.value = response.inventory || response.items || []
      total.value = response.total || inventory.value.length
    } finally {
      loading.value = false
    }
  }
  
  return {
    inventory,
    total,
    loading,
    fetchInventory,
  }
})

// 监控 Store
export const useMonitorsStore = defineStore('monitors', () => {
  const monitors = ref<MonitorTask[]>([])
  const loading = ref(false)
  
  async function fetchMonitors() {
    loading.value = true
    try {
      monitors.value = await monitorsApi.list()
    } finally {
      loading.value = false
    }
  }
  
  async function createMonitor(data: any) {
    await monitorsApi.create(data)
    await fetchMonitors()
  }
  
  async function deleteMonitor(id: number) {
    await monitorsApi.delete(id)
    await fetchMonitors()
  }
  
  return {
    monitors,
    loading,
    fetchMonitors,
    createMonitor,
    deleteMonitor,
  }
})

// 统计 Store
export const useStatsStore = defineStore('stats', () => {
  const dashboard = ref<DashboardStats | null>(null)
  const loading = ref(false)
  
  async function fetchDashboard() {
    loading.value = true
    try {
      dashboard.value = await statsApi.dashboard()
    } finally {
      loading.value = false
    }
  }
  
  return {
    dashboard,
    loading,
    fetchDashboard,
  }
})
