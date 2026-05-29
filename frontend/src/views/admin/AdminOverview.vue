<template>
  <div class="overview-page">
    <h1 class="page-title">📊 概览</h1>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: #fce7f3;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#db2777" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.user_count }}</span>
          <span class="stat-label">用户数</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #dbeafe;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="9" y1="21" x2="9" y2="9"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.scene_count }}</span>
          <span class="stat-label">场景数</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #dcfce7;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
            <polyline points="17 2 12 7 7 2"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.device_count }}</span>
          <span class="stat-label">设备数</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #fef3c7;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.pair_count }}</span>
          <span class="stat-label">图像对</span>
        </div>
      </div>
    </div>

    <div class="quick-links">
      <h3>快速入口</h3>
      <div class="link-grid">
        <button class="link-card" @click="$router.push('/admin/scenes')">
          <span class="link-icon">🏞️</span>
          <span class="link-label">场景管理</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/devices')">
          <span class="link-icon">📱</span>
          <span class="link-label">设备管理</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/images')">
          <span class="link-icon">🖼️</span>
          <span class="link-label">图像管理</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/batch-upload')">
          <span class="link-icon">📤</span>
          <span class="link-label">批量上传</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/pairs')">
          <span class="link-icon">🔗</span>
          <span class="link-label">配对管理</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/users')">
          <span class="link-icon">👤</span>
          <span class="link-label">用户管理</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/cleaning')">
          <span class="link-icon">🧹</span>
          <span class="link-label">数据清洗</span>
        </button>
        <button class="link-card" @click="$router.push('/admin/ranking')">
          <span class="link-icon">📈</span>
          <span class="link-label">排行榜</span>
        </button>
      </div>
    </div>

    <div class="guide-section">
      <h3>录入流程指引</h3>
      <div class="guide-steps">
        <div class="guide-step">
          <span class="step-num">1️⃣</span>
          <span>创建场景</span>
        </div>
        <span class="step-arrow">→</span>
        <div class="guide-step">
          <span class="step-num">2️⃣</span>
          <span>创建设备</span>
        </div>
        <span class="step-arrow">→</span>
        <div class="guide-step">
          <span class="step-num">3️⃣</span>
          <span>上传图像</span>
        </div>
        <span class="step-arrow">→</span>
        <div class="guide-step">
          <span class="step-num">4️⃣</span>
          <span>生成配对</span>
        </div>
      </div>
    </div>

    <div class="nav-section">
      <button class="btn-outline" @click="$router.push('/eval')">进入评测系统</button>
      <button class="btn-outline" @click="$router.push('/result')">查看评测结果</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetOverview } from '../../api/index.js'

const authStore = useAuthStore()

const stats = ref({
  scene_count: 0,
  device_count: 0,
  image_count: 0,
  pair_count: 0,
  eval_count: 0,
  user_count: 0,
})

async function fetchStats() {
  try {
    const data = await apiGetOverview()
    Object.assign(stats.value, data)
  } catch (e) {
    console.error('获取统计失败:', e)
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.overview-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value { font-size: 28px; font-weight: 700; color: #1e40af; }
.stat-label { font-size: 12px; color: #64748b; }

.quick-links, .guide-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.quick-links h3, .guide-section h3 {
  font-size: 14px;
  color: #374151;
  margin: 0 0 16px 0;
}

.link-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.link-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s;
}

.link-card:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

.link-icon { font-size: 24px; }
.link-label { font-size: 13px; color: #374151; font-weight: 500; }

.guide-steps {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #bae6fd;
}

.step-num { font-size: 18px; }

.step-arrow {
  color: #94a3b8;
  font-size: 20px;
}

.nav-section {
  display: flex;
  gap: 12px;
}

.btn-outline {
  flex: 1;
  padding: 14px 24px; background: #fff; color: #3b82f6;
  border: 2px solid #3b82f6; border-radius: 8px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.btn-outline:hover { background: #eff6ff; }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .link-grid { grid-template-columns: repeat(2, 1fr); }
  .guide-steps { flex-direction: column; }
  .step-arrow { transform: rotate(90deg); }
}
</style>
