<template>
  <div class="admin-layout">
    <header class="top-bar">
      <div class="bar-left">
        <span class="sys-name">图像盲评系统 - 管理后台</span>
      </div>
      <div class="bar-right">
        <span class="user-name">{{ authStore.user?.display_name || authStore.user?.username }}</span>
        <button class="btn-sm" @click="handleLogout">退出</button>
      </div>
    </header>

    <div class="admin-body">
      <nav class="sidebar">
        <div class="nav-item" :class="{ active: $route.name === 'AdminOverview' }" @click="$router.push('/admin/overview')">
          <span class="nav-icon">📊</span>
          <span class="nav-label">概览</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'SceneManage' }" @click="$router.push('/admin/scenes')">
          <span class="nav-icon">🏞️</span>
          <span class="nav-label">场景管理</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'DeviceManage' }" @click="$router.push('/admin/devices')">
          <span class="nav-icon">📷</span>
          <span class="nav-label">设备管理</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'ImageManage' }" @click="$router.push('/admin/images')">
          <span class="nav-icon">🖼️</span>
          <span class="nav-label">图像管理</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'BatchUpload' }" @click="$router.push('/admin/batch-upload')">
          <span class="nav-icon">📤</span>
          <span class="nav-label">批量上传</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'PairManage' }" @click="$router.push('/admin/pairs')">
          <span class="nav-icon">🔗</span>
          <span class="nav-label">配对管理</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'UserManage' }" @click="$router.push('/admin/users')">
          <span class="nav-icon">👥</span>
          <span class="nav-label">用户管理</span>
        </div>
        <div class="nav-divider"></div>
        <div class="nav-item" :class="{ active: $route.name === 'DataCleaning' }" @click="$router.push('/admin/cleaning')">
          <span class="nav-icon">🧹</span>
          <span class="nav-label">数据清洗</span>
        </div>
        <div class="nav-item" :class="{ active: $route.name === 'AdminLeaderboard' }" @click="$router.push('/admin/leaderboard')">
          <span class="nav-icon">🏆</span>
          <span class="nav-label">排行榜</span>
        </div>
      </nav>

      <main class="main-content">
        <router-view />
      </main>
    </div>

    <div class="toast-container">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        {{ t.msg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const toasts = ref([])
let toastId = 0

function showToast(msg, type = 'info') {
  const id = ++toastId
  toasts.value.push({ id, msg, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 3000)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function showToastParent(msg, type) {
  showToast(msg, type)
}

window.showAdminToast = showToastParent
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f5ff;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: white;
  border-bottom: 2px solid #dbeafe;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.bar-left { display: flex; align-items: center; }
.sys-name { font-size: 18px; font-weight: 700; color: #1e40af; }
.bar-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: #475569; }

.btn-sm {
  padding: 6px 14px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #fff; color: #64748b; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.btn-sm:hover { border-color: #3b82f6; color: #3b82f6; }

.admin-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  padding: 16px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f8fafc;
}

.nav-item.active {
  background: #eff6ff;
  border-left-color: #3b82f6;
}

.nav-icon {
  font-size: 20px;
  width: 24px;           /* 固定宽度，所有图标占位一样 */
  display: inline-flex;  /* 让内容居中 */
  justify-content: center;
  align-items: center;
}
.nav-label { font-size: 14px; font-weight: 500; color: #374151; }

.nav-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 8px 16px;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 300;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  animation: toastIn 0.3s ease, toastOut 0.3s ease 2.2s forwards;
}

.toast.info { background: #dbeafe; color: #1e40af; }
.toast.success { background: #dcfce7; color: #16a34a; }
.toast.error { background: #fef2f2; color: #dc2626; }

@keyframes toastIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes toastOut {
  from { opacity: 1; }
  to { opacity: 0; }
}

@media (max-width: 768px) {
  .admin-body { flex-direction: column; }
  .sidebar {
    width: 100%;
    flex-direction: row;
    padding: 8px;
    overflow-x: auto;
  }
  .nav-item { padding: 8px 12px; white-space: nowrap; }
  .nav-icon { font-size: 16px; }
  .nav-label { font-size: 13px; }
}
</style>
