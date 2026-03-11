// 库存 Store
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { inventoryApi, type InventoryItem, type InventoryListResponse, type InventorySummary } from '@/api/inventory'

export const useInventoryStore = defineStore('inventory', () => {
  // State
  const items = ref<InventoryItem[]>([])
  const summary = ref<InventorySummary | null>(null)
  const loading = ref(false)
  const refreshing = ref(false)
  
  // Getters
  const totalValue = computed(() => 
    items.value.reduce((sum, item) => sum + (item.price * item.amount), 0)
  )
  
  const totalItems = computed(() => 
    items.value.reduce((sum, item) => sum + item.amount, 0)
  )
  
  // Actions
  const fetchInventory = async (botId?: number) => {
    if (loading.value) return
    
    loading.value = true
    try {
      const response = await inventoryApi.getList({ bot_id: botId })
      const data = response.data as InventoryListResponse
      items.value = data.items
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
    } finally {
      loading.value = false
    }
  }
  
  const fetchSummary = async () => {
    try {
      const response = await inventoryApi.getSummary()
      summary.value = response.data as InventorySummary
    } catch (error) {
      console.error('Failed to fetch summary:', error)
    }
  }
  
  const refreshInventory = async (botId: number) => {
    refreshing.value = true
    try {
      await inventoryApi.refresh(botId)
      await fetchInventory(botId)
    } catch (error) {
      console.error('Failed to refresh inventory:', error)
    } finally {
      refreshing.value = false
    }
  }
  
  const fetchValuation = async () => {
    try {
      const response = await inventoryApi.getValuation()
      return response.data
    } catch (error) {
      console.error('Failed to fetch valuation:', error)
      return null
    }
  }
  
  return {
    items,
    summary,
    loading,
    refreshing,
    totalValue,
    totalItems,
    fetchInventory,
    fetchSummary,
    refreshInventory,
    fetchValuation
  }
})
