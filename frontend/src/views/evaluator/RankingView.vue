<template>
  <div class="ranking-page">
    <header class="top-bar">
      <div class="bar-left">
        <button v-if="!isAdminRoute" class="btn-back" @click="goBack">&larr; 返回</button>
        <span class="page-title">排行榜</span>
      </div>
      <div class="bar-right">
        <select v-if="authStore.isLoggedIn" v-model="selectedScene" class="scene-select" @change="fetchRanking">
          <option :value="null">综合排名</option>
          <option v-for="s in scenes" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <button class="btn-refresh" @click="fetchRanking">刷新</button>
      </div>
    </header>

    <!-- 模式切换（仅登录用户可见） -->
    <div v-if="authStore.isLoggedIn" class="mode-switch">
      <button :class="{ active: viewMode === 'single' }" @click="viewMode = 'single'">单场景</button>
      <button :class="{ active: viewMode === 'compare' }" @click="viewMode = 'compare'">多场景对比</button>
    </div>

    <!-- 场景对比选择器 -->
    <div v-if="viewMode === 'compare'" class="compare-selector">
      <div v-for="(sceneId, index) in compareScenes" :key="index" class="compare-item">
        <select v-model="compareScenes[index]" @change="onCompareSceneChange">
          <option :value="null">选择场景</option>
          <option v-for="s in scenes" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <button class="btn-remove" @click="removeCompareScene(index)">&times;</button>
      </div>
      <button v-if="compareScenes.length < 3" class="btn-add" @click="addCompareScene">+ 添加场景</button>
    </div>

    <main class="ranking-main">
      <!-- 加载状态 -->
      <div v-if="loading" class="center-msg">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!items.length" class="center-msg">
        <p>暂无排行榜数据</p>
        <p class="tip">请联系管理员执行数据清洗后生成排行榜</p>
      </div>

      <!-- 排行榜内容 -->
      <template v-else>
        <!-- 柱状图 -->
        <div class="chart-section">
          <div class="bar-chart">
            <div
              v-for="item in items"
              :key="item.device_id"
              class="bar-item"
            >
              <div class="bar-label">{{ item.device_name }}</div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: (item.score / 100 * 100) + '%', background: getBarColor(item.rank) }"
                ></div>
              </div>
              <div class="bar-value">{{ item.score.toFixed(1) }}</div>
            </div>
          </div>
        </div>

        <!-- 表格 -->
        <div class="table-section">
          <table class="ranking-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>机型名</th>
                <th>主芯片</th>
                <th>得分</th>
                <th>评测数</th>
                <th>置信区间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.device_id"
                  :class="{ 'clickable-row': authStore.isLoggedIn }"
                  @click="authStore.isLoggedIn && showDeviceDetail(item.device_id)">
                <td class="rank-cell">
                  <span class="rank-badge" :class="'rank-' + item.rank">{{ item.rank }}</span>
                </td>
                <td class="name-cell">{{ item.device_name }}</td>
                <td>{{ item.main_chip }}</td>
                <td class="score-cell">{{ item.score.toFixed(1) }}</td>
                <td>{{ item.eval_count }}</td>
                <td>&plusmn;{{ Math.abs(item.confidence_max).toFixed(1) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 对比结果 -->
      <div v-if="viewMode === 'compare' && compareData" class="compare-section">
        <!-- 对比表格 -->
        <div class="table-section">
          <table class="ranking-table">
            <thead>
              <tr>
                <th>设备</th>
                <th v-for="scene in compareData.scenes" :key="scene">{{ scene }}</th>
                <th>平均</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in compareData.items" :key="item.device_id">
                <td class="name-cell">{{ item.device_name }}</td>
                <td v-for="scene in compareData.scenes" :key="scene">
                  {{ item.scores[scene]?.toFixed(1) ?? '-' }}
                </td>
                <td class="score-cell">{{ item.average_score.toFixed(1) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- 设备详情弹窗 -->
    <div v-if="showDeviceModal" class="modal-overlay" @click.self="showDeviceModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ deviceDetail?.device_name }} 设备详情</h3>
          <button class="btn-close" @click="showDeviceModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="winrate-section">
            <h4>胜率分析</h4>
            <table class="data-table">
              <thead>
                <tr>
                  <th>对阵设备</th>
                  <th>胜场</th>
                  <th>负场</th>
                  <th>胜率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="wr in deviceDetail?.win_rates" :key="wr.opponent_id">
                  <td>{{ wr.opponent_name }}</td>
                  <td>{{ wr.win_count }}</td>
                  <td>{{ wr.lose_count }}</td>
                  <td>{{ (wr.win_rate * 100).toFixed(1) }}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="scene-rankings">
            <h4>各场景排名</h4>
            <table class="data-table">
              <thead>
                <tr>
                  <th>场景</th>
                  <th>排名</th>
                  <th>得分</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sr in deviceDetail?.scene_rankings" :key="sr.scene_name">
                  <td>{{ sr.scene_name }}</td>
                  <td>{{ sr.rank }}</td>
                  <td>{{ sr.score?.toFixed(1) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetRanking, apiGetScenes, apiGetDeviceWinRate, apiGetSceneCompare } from '../../api/index.js'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)

// 是否在管理员后台内
const isAdminRoute = computed(() => route.path.startsWith('/admin'))

function goBack() {
  if (authStore.isAdmin) {
    router.push('/admin')
  } else if (authStore.isLoggedIn) {
    router.push('/eval')
  } else {
    router.push('/login')
  }
}
const items = ref([])
const scenes = ref([])
const selectedScene = ref(null)
const showDeviceModal = ref(false)
const deviceDetail = ref(null)

const viewMode = ref('single')  // 'single' | 'compare'
const compareScenes = ref([])
const compareData = ref(null)

async function fetchScenes() {
  if (!authStore.isLoggedIn) return
  try {
    const data = await apiGetScenes()
    scenes.value = data || []
  } catch (e) {
    console.error('Failed to fetch scenes:', e)
  }
}

async function fetchRanking() {
  loading.value = true
  try {
    const data = await apiGetRanking(selectedScene.value)
    items.value = data.items || []
  } catch (e) {
    console.error('Failed to fetch ranking:', e)
    items.value = []
  } finally {
    loading.value = false
  }
}

async function showDeviceDetail(deviceId) {
  if (!authStore.isLoggedIn) return
  try {
    const data = await apiGetDeviceWinRate(deviceId)
    deviceDetail.value = data
    showDeviceModal.value = true
  } catch (e) {
    console.error('Failed to fetch device detail:', e)
  }
}

function getBarColor(rank) {
  if (rank === 1) return '#22c55e'
  if (rank === 2) return '#3b82f6'
  if (rank === 3) return '#f59e0b'
  return '#94a3b8'
}

async function fetchCompareData() {
  if (compareScenes.value.length === 0) return
  try {
    const data = await apiGetSceneCompare(compareScenes.value)
    compareData.value = data
  } catch (e) {
    console.error('Failed to fetch compare data:', e)
  }
}

function addCompareScene() {
  if (compareScenes.value.length < 3) {
    compareScenes.value.push(null)
  }
}

function removeCompareScene(index) {
  compareScenes.value.splice(index, 1)
  if (compareScenes.value.length > 0) {
    fetchCompareData()
  } else {
    compareData.value = null
  }
}

async function onCompareSceneChange() {
  await fetchCompareData()
}

onMounted(async () => {
  await fetchScenes()
  await fetchRanking()
})
</script>

<style scoped>
.ranking-page {
  min-height: 100vh;
  background: #f0f5ff;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 2px solid #dbeafe;
}
.bar-left { display: flex; align-items: center; gap: 12px; }
.bar-right { display: flex; align-items: center; gap: 10px; }
.page-title { font-size: 16px; font-weight: 700; color: #1e40af; }

.btn-back, .btn-refresh {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
}
.btn-back:hover, .btn-refresh:hover { border-color: #3b82f6; color: #3b82f6; }

.scene-select {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
}

.ranking-main { padding: 24px; }

.center-msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #64748b;
}
.center-msg .tip { font-size: 13px; color: #94a3b8; margin-top: 8px; }

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #dbeafe; border-top-color: #3b82f6;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 柱状图 */
.chart-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid #e2e8f0;
}
.bar-chart { display: flex; flex-direction: column; gap: 12px; }
.bar-item { display: flex; align-items: center; gap: 12px; }
.bar-label { width: 120px; font-size: 13px; font-weight: 500; color: #334155; text-align: right; }
.bar-track { flex: 1; height: 28px; background: #f1f5f9; border-radius: 6px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
.bar-value { width: 50px; font-size: 14px; font-weight: 700; color: #1e40af; }

/* 表格 */
.table-section {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.ranking-table { width: 100%; border-collapse: collapse; }
.ranking-table th {
  padding: 12px 16px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}
.ranking-table td {
  padding: 14px 16px;
  font-size: 13px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}
.rank-cell { text-align: center; }
.rank-badge {
  display: inline-block;
  width: 28px; height: 28px;
  border-radius: 50%;
  line-height: 28px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  background: #f1f5f9;
  color: #64748b;
}
.rank-1 { background: #dcfce7; color: #16a34a; }
.rank-2 { background: #dbeafe; color: #2563eb; }
.rank-3 { background: #fef3c7; color: #d97706; }
.name-cell { font-weight: 600; color: #1e40af; }
.score-cell { font-weight: 700; color: #1e40af; }
.clickable-row { cursor: pointer; }
.clickable-row:hover { background: #f0f5ff; }

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e40af;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
}

.btn-close:hover { color: #475569; }

.modal-body {
  padding: 24px;
}

.winrate-section, .scene-rankings {
  margin-bottom: 24px;
}

.winrate-section h4, .scene-rankings h4 {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 10px 12px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.data-table td {
  padding: 10px 12px;
  font-size: 13px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}

.mode-switch {
  display: flex;
  gap: 8px;
  padding: 16px 24px 0;
  margin-bottom: 16px;
}

.mode-switch button {
  padding: 8px 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.mode-switch button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.compare-selector {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding: 0 24px 16px;
  margin-bottom: 16px;
}

.compare-item {
  display: flex;
  gap: 4px;
}

.compare-item select {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
}

.btn-remove {
  padding: 6px 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  cursor: pointer;
}

.btn-add {
  padding: 6px 12px;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
  color: #16a34a;
  cursor: pointer;
}

.compare-section {
  margin-top: 24px;
}
</style>
