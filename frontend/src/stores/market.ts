// 市场 Store
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { itemsApi, type Item, type ItemListResponse } from '@/api/items'

export const useMarketStore = defineStore('market', () => {
  // State
  const items = ref<Item[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)
  
  // Filters
  const filters = ref({
    category: '',
    rarity: '',
    exterior: '',
    minPrice: 0,
    maxPrice: 0,
    sortBy: 'current_price',
    sortOrder: 'asc'
  })
  
  // Getters
  const hasMore = computed(() => items.value.length < total.value)
  
  // Actions
  const fetchItems = async (reset: boolean = false) => {
    if (loading.value) return
    
    loading.value = true
    try {
      if (reset) {
        currentPage.value = 1
        items.value = []
      }
      
      const response = await itemsApi.getList({
        page: currentPage.value,
        page_size: pageSize.value,
        category: filters.value.category || undefined,
        rarity: filters.value.rarity || undefined,
        exterior: filters.value.exterior || undefined,
        min_price: filters.value.minPrice || undefined,
        max_price: filters.value.maxPrice || undefined,
        sort_by: filters.value.sortBy,
        sort_order: filters.value.sortOrder
      })
      
      const data = response.data as ItemListResponse
      if (reset) {
        items.value = data.items
      } else {
        items.value = [...items.value, ...data.items]
      }
      total.value = data.total
    } catch (error) {
      console.error('Failed to fetch items:', error)
    } finally {
      loading.value = false
    }
  }
  
  const loadMore = async () => {
    if (!hasMore.value || loading.value) return
    currentPage.value++
    await fetchItems()
  }
  
  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
    fetchItems(true)
  }
  
  const searchItems = async (keyword: string) => {
    loading.value = true
    try {
      const response = await itemsApi.search(keyword)
      const data = response.data as { items: Item[] }
      items.value = data.items
      total.value = data.items.length
    } catch (error) {
      console.error('Failed to search items:', error)
    } finally {
      loading.value = false
    }
  }
  
  return {
    items,
    total,
    loading,
    currentPage,
    pageSize,
    filters,
    hasMore,
    fetchItems,
    loadMore,
    setFilters,
    searchItems
  }
})
