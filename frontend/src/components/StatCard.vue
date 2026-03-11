<template>
  <div class="stat-card" :class="[variant, { clickable }]" @click="handleClick">
    <div class="stat-header">
      <div class="stat-icon">{{ icon }}</div>
      <div v-if="trend" class="stat-trend" :class="trendDirection">
        <span>{{ trendDirection === 'up' ? '↑' : '↓' }}</span>
        <span>{{ Math.abs(trend) }}%</span>
      </div>
    </div>
    
    <div class="stat-content">
      <div class="stat-value">
        <span v-if="prefix" class="stat-prefix">{{ prefix }}</span>
        <span class="value">{{ formattedValue }}</span>
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
      <div class="stat-label">{{ label }}</div>
    </div>
    
    <div v-if="$slots.footer" class="stat-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value: number | string
  label: string
  icon?: string
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
  prefix?: string
  suffix?: string
  trend?: number
  decimals?: number
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  decimals: 2,
  clickable: false
})

const emit = defineEmits(['click'])

const trendDirection = computed(() => {
  if (!props.trend) return null
  return props.trend > 0 ? 'up' : 'down'
})

const formattedValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  
  return props.value.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: props.decimals
  })
})

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped>
.stat-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #16213e;
  transition: all 0.3s ease;
}

.stat-card.clickable {
  cursor: pointer;
}

.stat-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.stat-card.primary {
  border-color: #00d4ff;
}

.stat-card.primary .stat-icon {
  background: rgba(0, 212, 255, 0.1);
}

.stat-card.success {
  border-color: #00ff88;
}

.stat-card.success .stat-icon {
  background: rgba(0, 255, 136, 0.1);
}

.stat-card.warning {
  border-color: #ffaa00;
}

.stat-card.warning .stat-icon {
  background: rgba(255, 170, 0, 0.1);
}

.stat-card.danger {
  border-color: #ff4444;
}

.stat-card.danger .stat-icon {
  background: rgba(255, 68, 68, 0.1);
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.stat-trend.up {
  background: rgba(0, 255, 136, 0.1);
  color: #00ff88;
}

.stat-trend.down {
  background: rgba(255, 68, 68, 0.1);
  color: #ff4444;
}

.stat-content {
  margin-bottom: 12px;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
}

.stat-prefix {
  font-size: 20px;
  color: #888;
}

.value {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.stat-suffix {
  font-size: 14px;
  color: #888;
}

.stat-label {
  font-size: 14px;
  color: #888;
}

.stat-footer {
  padding-top: 12px;
  border-top: 1px solid #16213e;
  font-size: 12px;
  color: #888;
}
</style>
