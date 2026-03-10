export { useUserStore } from './user'

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { itemsApi, ordersApi, inventoryApi, monitorsApi, statsApi } from '@/utils/api'
import type { Item, Order, Inventory, MonitorTask, DashboardStats } from '@/types'

// 饰品 Store
export const useItemsStore = defineStore('items', () => {
  const items = ref<Item[]>([])
  const currentItem = ref<Item | null>(null)
  const total = ref(0)
  const loading = ref(false)
  
  async function fetchItems(params: any = {}) {
    loading.value = true
    try {
      const res: any = await itemsApi.list(params)
      items.value = res.data?.items || res.items || []
      total.value = res.data?.total || res.total || 0
    } finally {
      loading.value = false
    }
  }
  
  async function searchItems(keyword: string) {
    const res: any = await itemsApi.search(keyword)
    return res.data?.items || res.items || []
  }
  
  async function getItem(id: number) {
    const res: any = await itemsApi.get(id)
    currentItem.value = res.data || res
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
      const res: any = await ordersApi.list(params)
      orders.value = res.data?.orders || res.orders || []
      total.value = res.data?.total || res.total || 0
    } finally {
      loading.value = false
    }
  }
  
  async function createOrder(data: any) {
    const res: any = await ordersApi.create(data)
    return res.data || res
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
      const res: any = await inventoryApi.list(params)
      inventory.value = res.data?.inventory || res.inventory || res.data?.items || res.items || []
      total.value = res.data?.total || res.total || inventory.value.length
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
      const res: any = await monitorsApi.list()
      monitors.value = res.data || res || []
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
      const res: any = await statsApi.dashboard()
      dashboard.value = res.data || res
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
