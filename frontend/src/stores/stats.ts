// 统计 Store
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { statsApi, type DashboardStats, type TradingStats, type ProfitStats } from '@/api/stats'

export const useStatsStore = defineStore('stats', () => {
  // State
  const dashboard = ref<DashboardStats | null>(null)
  const trading = ref<TradingStats | null>(null)
  const profit = ref<ProfitStats | null>(null)
  const loading = ref(false)
  const period = ref<number>(7) // 默认7天
  
  // Actions
  const fetchDashboard = async () => {
    loading.value = true
    try {
      const response = await statsApi.getDashboard()
      dashboard.value = response.data as DashboardStats
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error)
    } finally {
      loading.value = false
    }
  }
  
  const fetchTrading = async (days?: number) => {
    try {
      const response = await statsApi.getTrading({ days: days || period.value })
      trading.value = response.data as TradingStats
    } catch (error) {
      console.error('Failed to fetch trading stats:', error)
    }
  }
  
  const fetchProfit = async (days?: number) => {
    try {
      const response = await statsApi.getProfit({ days: days || period.value })
      profit.value = response.data as ProfitStats
    } catch (error) {
      console.error('Failed to fetch profit stats:', error)
    }
  }
  
  const fetchAll = async (days: number = 7) => {
    period.value = days
    loading.value = true
    try {
      await Promise.all([
        fetchDashboard(),
        fetchTrading(days),
        fetchProfit(days)
      ])
    } finally {
      loading.value = false
    }
  }
  
  const setPeriod = (days: number) => {
    fetchAll(days)
  }
  
  return {
    dashboard,
    trading,
    profit,
    loading,
    period,
    fetchDashboard,
    fetchTrading,
    fetchProfit,
    fetchAll,
    setPeriod
  }
})
