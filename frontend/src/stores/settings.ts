// 设置 Store
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface AppSettings {
  // 主题
  theme: 'light' | 'dark' | 'auto'
  // 语言
  language: 'zh-CN' | 'en-US'
  // 通知
  notifications: {
    orderCompleted: boolean
    priceAlert: boolean
    inventoryAlert: boolean
    systemNews: boolean
  }
  // 交易设置
  trading: {
    defaultQuantity: number
    autoConfirm: boolean
    priceChangeThreshold: number
  }
  // 界面设置
  ui: {
    sidebarCollapsed: boolean
    pageSize: number
    showPrices: boolean
  }
}

const defaultSettings: AppSettings = {
  theme: 'dark',
  language: 'zh-CN',
  notifications: {
    orderCompleted: true,
    priceAlert: true,
    inventoryAlert: true,
    systemNews: true
  },
  trading: {
    defaultQuantity: 1,
    autoConfirm: false,
    priceChangeThreshold: 5
  },
  ui: {
    sidebarCollapsed: false,
    pageSize: 20,
    showPrices: true
  }
}

export const useSettingsStore = defineStore('settings', () => {
  // 从 localStorage 加载设置
  const loadSettings = (): AppSettings => {
    try {
      const stored = localStorage.getItem('app-settings')
      if (stored) {
        return { ...defaultSettings, ...JSON.parse(stored) }
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
    return { ...defaultSettings }
  }
  
  const settings = ref<AppSettings>(loadSettings())
  
  // 监听设置变化并保存
  watch(settings, (newValue) => {
    localStorage.setItem('app-settings', JSON.stringify(newValue))
  }, { deep: true })
  
  // Actions
  const updateSettings = (partial: Partial<AppSettings>) => {
    settings.value = { ...settings.value, ...partial }
  }
  
  const resetSettings = () => {
    settings.value = { ...defaultSettings }
  }
  
  const updateTheme = (theme: AppSettings['theme']) => {
    settings.value.theme = theme
    // 应用主题
    document.documentElement.setAttribute('data-theme', theme === 'auto' ? 'dark' : theme)
  }
  
  const updateLanguage = (language: AppSettings['language']) => {
    settings.value.language = language
  }
  
  const updateNotifications = (key: keyof AppSettings['notifications'], value: boolean) => {
    settings.value.notifications[key] = value
  }
  
  const updateTradingSettings = (key: keyof AppSettings['trading'], value: any) => {
    (settings.value.trading as any)[key] = value
  }
  
  const updateUISettings = (key: keyof AppSettings['ui'], value: any) => {
    (settings.value.ui as any)[key] = value
  }
  
  return {
    settings,
    updateSettings,
    resetSettings,
    updateTheme,
    updateLanguage,
    updateNotifications,
    updateTradingSettings,
    updateUISettings
  }
})
