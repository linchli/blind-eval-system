<template>
  <div class="result-page">
    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="bar-left">
        <span class="sys-name">评测结果</span>
      </div>
      <div class="bar-right">
        <button class="btn-sm" @click="$router.push('/eval')">返回评测</button>
        <button class="btn-sm" @click="handleLogout">退出</button>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="result-main">
      <div class="result-card" v-if="!loading && evaluations.length > 0">
        <div class="card-header">
          <h2>我的评测记录</h2>
          <button class="btn-outline" @click="exportCSV">导出CSV</button>
        </div>

        <!-- 统计概览 -->
        <div class="stats-overview">
          <div class="stat-box">
            <span class="stat-num">{{ evaluations.length }}</span>
            <span class="stat-label">已完成评测</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{{ totalPairs }}</span>
            <span class="stat-label">总图对数</span>
          </div>
          <div class="stat-box">
            <span class="stat-num">{{ progressPercent }}%</span>
            <span class="stat-label">完成进度</span>
          </div>
        </div>

        <!-- 评分分布 -->
        <div class="score-distribution">
          <h3>评分分布</h3>
          <div class="dist-bars">
            <div class="dist-item">
              <span class="dist-label">A更好</span>
              <div class="dist-bar-wrap">
                <div class="dist-bar" :style="{ width: getDistPercent('a_much') + '%' }"></div>
              </div>
              <span class="dist-count">{{ distribution.a_much }}</span>
            </div>
            <div class="dist-item">
              <span class="dist-label">A稍好</span>
              <div class="dist-bar-wrap">
                <div class="dist-bar" :style="{ width: getDistPercent('a_slight') + '%' }"></div>
              </div>
              <span class="dist-count">{{ distribution.a_slight }}</span>
            </div>
            <div class="dist-item">
              <span class="dist-label">一样好</span>
              <div class="dist-bar-wrap">
                <div class="dist-bar" :style="{ width: getDistPercent('same') + '%' }"></div>
              </div>
              <span class="dist-count">{{ distribution.same }}</span>
            </div>
            <div class="dist-item">
              <span class="dist-label">B稍好</span>
              <div class="dist-bar-wrap">
                <div class="dist-bar" :style="{ width: getDistPercent('b_slight') + '%' }"></div>
              </div>
              <span class="dist-count">{{ distribution.b_slight }}</span>
            </div>
            <div class="dist-item">
              <span class="dist-label">B更好</span>
              <div class="dist-bar-wrap">
                <div class="dist-bar" :style="{ width: getDistPercent('b_much') + '%' }"></div>
              </div>
              <span class="dist-count">{{ distribution.b_much }}</span>
            </div>
          </div>
        </div>

        <!-- 评测记录列表 -->
        <div class="records-list">
          <h3>评测详情</h3>
          <div class="records-table">
            <table>
              <thead>
                <tr>
                  <th>序号</th>
                  <th>图对ID</th>
                  <th>评分</th>
                  <th>提交时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(ev, idx) in evaluations" :key="ev.id">
                  <td>{{ idx + 1 }}</td>
                  <td>{{ ev.pair_id }}</td>
                  <td>
                    <span class="score-badge" :class="'score-' + ev.score">
                      {{ getScoreLabel(ev.score) }}
                    </span>
                  </td>
                  <td>{{ formatTime(ev.submitted_at || ev.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading && evaluations.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none"
             stroke="#94a3b8" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <h3>暂无评测记录</h3>
        <p>完成评测后，这里将显示您的评测结果</p>
        <button class="btn-primary" @click="$router.push('/eval')">开始评测</button>
      </div>

      <!-- 加载中 -->
      <div v-else class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetMyEvals, apiGetProgress, apiExportCSV, apiGetEvalStatus } from '../../api/index.js'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const evaluations = ref([])
const totalPairs = ref(0)
const distribution = reactive({
  a_much: 0,
  a_slight: 0,
  same: 0,
  b_slight: 0,
  b_much: 0
})

const progressPercent = computed(() => {
  if (!totalPairs.value) return 0
  return Math.round((evaluations.value.length / totalPairs.value) * 100)
})

function getScoreLabel(score) {
  const labels = {
    'a_much': 'A更好',
    'a_slight': 'A稍好',
    'same': '一样好',
    'b_slight': 'B稍好',
    'b_much': 'B更好'
  }
  return labels[score] || score
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN')
}

function getDistPercent(scoreKey) {
  const total = evaluations.value.length
  if (!total) return 0
  return Math.round((distribution[scoreKey] / total) * 100)
}

async function fetchData() {
  loading.value = true
  try {
    // 获取评测记录
    const evals = await apiGetMyEvals()
    evaluations.value = evals || []

    // 只统计 submitted 状态
    const submittedEvals = evaluations.value.filter(e => e.status !== 'draft')

    // 计算分布
    Object.keys(distribution).forEach(k => distribution[k] = 0)
    submittedEvals.forEach(e => {
      if (e.score in distribution) {
        distribution[e.score]++
      }
    })

    // 获取总图对数
    const status = await apiGetEvalStatus()
    totalPairs.value = status.total_pairs || 0

  } catch (e) {
    console.error('获取数据失败:', e)
  } finally {
    loading.value = false
  }
}

async function exportCSV() {
  try {
    const resp = await apiExportCSV()
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `盲评结果_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('导出失败: ' + e.message)
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background: #f0f5ff;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: white;
  border-bottom: 2px solid #dbeafe;
}

.bar-left { display: flex; align-items: center; }
.sys-name { font-size: 18px; font-weight: 700; color: #1e40af; }
.bar-right { display: flex; gap: 10px; }

.btn-sm {
  padding: 6px 14px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #fff; color: #64748b; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.btn-sm:hover { border-color: #3b82f6; color: #3b82f6; }

.result-main {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.result-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h2 { font-size: 18px; color: #1e40af; margin: 0; }

.btn-outline {
  padding: 8px 16px; background: #fff; color: #3b82f6;
  border: 2px solid #3b82f6; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.btn-outline:hover { background: #eff6ff; }

.stats-overview {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.stat-num { font-size: 32px; font-weight: 700; color: #1e40af; }
.stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }

.score-distribution {
  margin-bottom: 24px;
}

.score-distribution h3, .records-list h3 {
  font-size: 14px;
  color: #374151;
  margin: 0 0 12px 0;
}

.dist-bars { display: flex; flex-direction: column; gap: 10px; }

.dist-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dist-label { width: 60px; font-size: 13px; color: #64748b; }
.dist-bar-wrap { flex: 1; height: 20px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.dist-bar { height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 4px; transition: width 0.3s; }
.dist-count { width: 30px; font-size: 13px; font-weight: 600; color: #1e40af; text-align: right; }

.records-table { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

th {
  background: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

td { font-size: 13px; color: #374151; }

.score-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.score-a_much { background: #dbeafe; color: #1d4ed8; }
.score-a_slight { background: #eff6ff; color: #2563eb; }
.score-same { background: #f1f5f9; color: #475569; }
.score-b_slight { background: #ffedd5; color: #c2410c; }
.score-b_much { background: #fff7ed; color: #ea580c; }

.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: white;
  border-radius: 12px;
  text-align: center;
}

.empty-state h3 { font-size: 18px; color: #374151; margin: 16px 0 8px; }
.empty-state p { color: #64748b; margin-bottom: 20px; }

.btn-primary {
  padding: 10px 24px; background: #3b82f6; color: #fff;
  border: none; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.btn-primary:hover { background: #2563eb; }

.loading-state { gap: 12px; }

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #dbeafe; border-top-color: #3b82f6;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
