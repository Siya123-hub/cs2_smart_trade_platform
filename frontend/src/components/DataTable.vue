<template>
  <div class="data-table-container">
    <div v-if="title" class="table-header">
      <h3>{{ title }}</h3>
      <div class="table-actions">
        <slot name="actions"></slot>
      </div>
    </div>
    
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th 
              v-for="col in columns" 
              :key="col.key"
              :style="{ width: col.width, textAlign: col.align || 'left' }"
              @click="col.sortable && handleSort(col.key)"
            >
              {{ col.label }}
              <span v-if="col.sortable && sortKey === col.key" class="sort-icon">
                {{ sortOrder === 'asc' ? '↑' : '↓' }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="columns.length" class="loading-cell">
              <span class="loading-spinner"></span>
              加载中...
            </td>
          </tr>
          <tr v-else-if="!data.length">
            <td :colspan="columns.length" class="empty-cell">
              {{ emptyText }}
            </td>
          </tr>
          <tr 
            v-else
            v-for="(row, index) in paginatedData" 
            :key="row.id || index"
            @click="handleRowClick(row)"
          >
            <td 
              v-for="col in columns" 
              :key="col.key"
              :style="{ textAlign: col.align || 'left' }"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div v-if="pagination && data.length > 0" class="table-footer">
      <div class="page-info">
        共 {{ total }} 条，第 {{ currentPage }}/{{ totalPages }} 页
      </div>
      <div class="pagination">
        <button 
          :disabled="currentPage === 1" 
          @click="handlePageChange(currentPage - 1)"
        >
          上一页
        </button>
        <button 
          v-for="page in visiblePages" 
          :key="page"
          :class="{ active: page === currentPage }"
          @click="handlePageChange(page)"
        >
          {{ page }}
        </button>
        <button 
          :disabled="currentPage === totalPages" 
          @click="handlePageChange(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Column {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
}

interface Props {
  columns: Column[]
  data: any[]
  title?: string
  loading?: boolean
  emptyText?: string
  pagination?: boolean
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  emptyText: '暂无数据',
  pagination: true,
  pageSize: 20
})

const emit = defineEmits(['sort', 'page-change', 'row-click'])

const sortKey = ref('')
const sortOrder = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)

const total = computed(() => props.data.length)
const totalPages = computed(() => Math.ceil(total.value / props.pageSize))

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  
  return [...props.data].sort((a, b) => {
    const aVal = a[sortKey.value]
    const bVal = b[sortKey.value]
    
    if (sortOrder.value === 'asc') {
      return aVal > bVal ? 1 : -1
    }
    return aVal < bVal ? 1 : -1
  })
})

const paginatedData = computed(() => {
  if (!props.pagination) return sortedData.value
  
  const start = (currentPage.value - 1) * props.pageSize
  return sortedData.value.slice(start, start + props.pageSize)
})

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

const handleSort = (key: string) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
  emit('sort', { key: sortKey.value, order: sortOrder.value })
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  emit('page-change', page)
}

const handleRowClick = (row: any) => {
  emit('row-click', row)
}
</script>

<style scoped>
.data-table-container {
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #16213e;
}

.table-header h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #16213e;
}

th {
  padding: 12px 16px;
  color: #888;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  cursor: pointer;
  user-select: none;
}

th:hover {
  color: #fff;
}

.sort-icon {
  margin-left: 4px;
  color: #00d4ff;
}

tbody tr {
  border-bottom: 1px solid #16213e;
  cursor: pointer;
  transition: background 0.2s;
}

tbody tr:hover {
  background: #16213e;
}

td {
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
}

.loading-cell,
.empty-cell {
  text-align: center;
  color: #888;
  padding: 40px 16px;
}

.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid #16213e;
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid #16213e;
}

.page-info {
  color: #888;
  font-size: 12px;
}

.pagination {
  display: flex;
  gap: 4px;
}

.pagination button {
  padding: 6px 12px;
  background: #16213e;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

.pagination button:hover:not(:disabled) {
  background: #0f3460;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination button.active {
  background: #00d4ff;
  color: #000;
}
</style>
