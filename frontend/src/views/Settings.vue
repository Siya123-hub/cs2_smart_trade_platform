<template>
  <div class="settings-page">
    <div class="settings-header">
      <h1>⚙️ 设置</h1>
    </div>
    
    <div class="settings-content">
      <!-- 主题设置 -->
      <div class="settings-section">
        <h2>外观</h2>
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">主题</span>
            <span class="label-desc">选择界面主题风格</span>
          </div>
          <div class="setting-control">
            <select v-model="settings.theme" @change="handleThemeChange">
              <option value="dark">深色</option>
              <option value="light">浅色</option>
              <option value="auto">跟随系统</option>
            </select>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">语言</span>
            <span class="label-desc">选择界面显示语言</span>
          </div>
          <div class="setting-control">
            <select v-model="settings.language" @change="handleLanguageChange">
              <option value="zh-CN">简体中文</option>
              <option value="en-US">English</option>
            </select>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">侧边栏</span>
            <span class="label-desc">默认收起侧边栏</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.ui.sidebarCollapsed">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
      
      <!-- 通知设置 -->
      <div class="settings-section">
        <h2>通知</h2>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">订单完成</span>
            <span class="label-desc">订单状态变化时通知</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.notifications.orderCompleted">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">价格提醒</span>
            <span class="label-desc">饰品价格达到目标时通知</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.notifications.priceAlert">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">库存预警</span>
            <span class="label-desc">库存异常时通知</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.notifications.inventoryAlert">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">系统公告</span>
            <span class="label-desc">接收系统更新和公告</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.notifications.systemNews">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
      
      <!-- 交易设置 -->
      <div class="settings-section">
        <h2>交易</h2>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">默认数量</span>
            <span class="label-desc">下单时的默认购买数量</span>
          </div>
          <div class="setting-control">
            <input 
              type="number" 
              v-model.number="settings.trading.defaultQuantity" 
              min="1" 
              max="100"
            >
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">自动确认</span>
            <span class="label-desc">下单时直接执行，不二次确认</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.trading.autoConfirm">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">价格波动阈值</span>
            <span class="label-desc">超过此百分比时提醒 (%)</span>
          </div>
          <div class="setting-control">
            <input 
              type="number" 
              v-model.number="settings.trading.priceChangeThreshold" 
              min="0" 
              max="50"
            >
          </div>
        </div>
      </div>
      
      <!-- 界面设置 -->
      <div class="settings-section">
        <h2>界面</h2>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">每页显示</span>
            <span class="label-desc">列表每页显示的条目数</span>
          </div>
          <div class="setting-control">
            <select v-model.number="settings.ui.pageSize">
              <option :value="10">10 条</option>
              <option :value="20">20 条</option>
              <option :value="50">50 条</option>
              <option :value="100">100 条</option>
            </select>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">显示价格</span>
            <span class="label-desc">在界面中显示价格信息</span>
          </div>
          <div class="setting-control">
            <label class="toggle">
              <input type="checkbox" v-model="settings.ui.showPrices">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
      
      <!-- 操作 -->
      <div class="settings-actions">
        <button class="btn btn-secondary" @click="resetSettings">
          重置为默认
        </button>
        <button class="btn btn-primary" @click="saveSettings">
          保存设置
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import { useSettingsStore, type AppSettings } from '@/stores/settings'

const settingsStore = useSettingsStore()

const settings = reactive<AppSettings>({
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
})

onMounted(() => {
  // 加载设置
  Object.assign(settings, settingsStore.settings)
})

const handleThemeChange = () => {
  settingsStore.updateTheme(settings.theme)
}

const handleLanguageChange = () => {
  settingsStore.updateLanguage(settings.language)
}

const saveSettings = () => {
  settingsStore.updateSettings(settings)
  alert('设置已保存')
}

const resetSettings = () => {
  if (confirm('确定要重置所有设置为默认值吗？')) {
    settingsStore.resetSettings()
    Object.assign(settings, settingsStore.settings)
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.settings-header {
  margin-bottom: 30px;
}

.settings-header h1 {
  color: #fff;
  font-size: 28px;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
}

.settings-section h2 {
  color: #fff;
  font-size: 18px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #16213e;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid #16213e;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label-text {
  color: #fff;
  font-size: 14px;
}

.label-desc {
  color: #888;
  font-size: 12px;
}

.setting-control {
  display: flex;
  align-items: center;
}

.setting-control select,
.setting-control input[type="number"] {
  padding: 8px 12px;
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  outline: none;
  min-width: 120px;
}

.setting-control select:focus,
.setting-control input:focus {
  border-color: #00d4ff;
}

/* Toggle Switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #16213e;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: #fff;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle input:checked + .toggle-slider {
  background-color: #00d4ff;
}

.toggle input:checked + .toggle-slider:before {
  transform: translateX(24px);
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
}

.btn {
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-secondary {
  background: #16213e;
  color: #fff;
}

.btn-secondary:hover {
  background: #0f3460;
}

.btn-primary {
  background: #00d4ff;
  color: #000;
}

.btn-primary:hover {
  background: #00b8e6;
}
</style>
