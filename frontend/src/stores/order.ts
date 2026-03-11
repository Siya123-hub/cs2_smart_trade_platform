// 订单 Store
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ordersApi, type Order, type OrderListResponse, type CreateOrderData } from '@/api/orders'

export const useOrderStore = defineStore('order', () => {
  // State
  const orders = ref<Order[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)
  
  // Filters
  const filters = ref({
    status: '',
    side: '',
    source: ''
  })
  
  // Getters
  const pendingOrders = computed(() => 
    orders.value.filter(o => o.status === 'pending')
  )
  
  const completedOrders = computed(() => 
    orders.value.filter(o => o.status === 'completed')
  )
  
  // Actions
  const fetchOrders = async (reset: boolean = false) => {
    if (loading.value) return
    
    loading.value = true
    try {
      if (reset) {
        currentPage.value = 1
        orders.value = []
      }
      
      const response = await ordersApi.getList({
        page: currentPage.value,
        page_size: pageSize.value,
        status: filters.value.status || undefined,
        side: filters.value.side || undefined,
        source: filters.value.source || undefined
      })
      
      const data = response.data as OrderListResponse
      if (reset) {
        orders.value = data.orders
      } else {
        orders.value = [...orders.value, ...data.orders]
      }
      total.value = data.total
    } catch (error) {
      console.error('Failed to fetch orders:', error)
    } finally {
      loading.value = false
    }
  }
  
  const createOrder = async (data: CreateOrderData) => {
    try {
      const response = await ordersApi.create(data)
      const newOrder = response.data as Order
      orders.value.unshift(newOrder)
      total.value++
      return newOrder
    } catch (error) {
      console.error('Failed to create order:', error)
      throw error
    }
  }
  
  const cancelOrder = async (id: number) => {
    try {
      await ordersApi.cancel(id)
      const index = orders.value.findIndex(o => o.id === id)
      if (index !== -1) {
        orders.value[index].status = 'cancelled'
      }
    } catch (error) {
      console.error('Failed to cancel order:', error)
      throw error
    }
  }
  
  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
    fetchOrders(true)
  }
  
  return {
    orders,
    total,
    loading,
    currentPage,
    pageSize,
    filters,
    pendingOrders,
    completedOrders,
    fetchOrders,
    createOrder,
    cancelOrder,
    setFilters
  }
})
