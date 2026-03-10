<template>
  <div class="dashboard">
    <el-container>
      <el-aside width="200px">
        <div class="logo">CS2 Trade</div>
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar"
        >
          <el-menu-item index="/dashboard">
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/items">
            <span>饰品市场</span>
          </el-menu-item>
          <el-menu-item index="/orders">
            <span>订单管理</span>
          </el-menu-item>
          <el-menu-item index="/inventory">
            <span>我的库存</span>
          </el-menu-item>
          <el-menu-item index="/monitors">
            <span>价格监控</span>
          </el-menu-item>
          <el-menu-item index="/bots">
            <span>机器人</span>
          </el-menu-item>
          <el-menu-item index="/stats">
            <span>数据统计</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-container>
        <el-header>
          <div class="header-right">
            <span class="username">{{ userStore.user?.username }}</span>
            <el-button @click="handleLogout" size="small">退出</el-button>
          </div>
        </el-header>
        
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore, useStatsStore } from '@/stores'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const statsStore = useStatsStore()

const activeMenu = computed(() => route.path)

onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  statsStore.fetchDashboard()
})

function handleLogout() {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #304156;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 20px;
  font-weight: bold;
}

.sidebar {
  border-right: none;
  background-color: #304156;
}

.sidebar .el-menu-item {
  color: #bfcbd9;
}

.sidebar .el-menu-item:hover,
.sidebar .el-menu-item.is-active {
  background-color: #263445;
  color: #409eff;
}

.el-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.username {
  color: #606266;
}

.el-main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
