<template>
  <div class="leaderboard-page">
    <h1 class="page-title">🏆 设备排行榜</h1>

    <!-- 标签页 -->
    <div class="tabs">
      <button :class="{ active: activeTab === 'ranking' }" @click="activeTab = 'ranking'">
        排行榜
      </button>
      <button v-if="authStore.isAdmin" :class="{ active: activeTab === 'detail' }" @click="activeTab = 'detail'">
        详细数据
      </button>
    </div>

    <!-- Tab 1: 排行榜 -->
    <div v-if="activeTab === 'ranking'">
      <!-- 筛选条件 - 三级排列 -->
      <div class="filter-panel">
        <!-- 第一级：得分类型 -->
        <div class="filter-section">
          <span class="filter-label">得分类型：</span>
          <div class="filter-group">
            <button :class="{ active: filters.score_type === 'bt' }" @click="filters.score_type = 'bt'; fetchLeaderboard()">BT得分</button>
            <button :class="{ active: filters.score_type === 'mean' }" @click="filters.score_type = 'mean'; fetchLeaderboard()">评分均值</button>
          </div>
        </div>

        <!-- 第二级：场景级别筛选 -->
        <div class="filter-section">
          <span class="filter-label">场景筛选：</span>
          <div class="filter-group">
            <select v-model="filters.scene" @change="onSceneChange">
              <option value="">全部场景</option>
              <option v-for="scene in filterOptions.scenes" :key="scene.id" :value="'scene:'+scene.id">
                {{ scene.name }}
              </option>
            </select>
            <select v-model="filters.category" @change="onCategoryChange">
              <option value="">全部大类</option>
              <option v-for="cat in filterOptions.categories" :key="cat.id" :value="cat.name">
                {{ cat.name }}
              </option>
            </select>
            <select v-model="filters.location" @change="onLocationChange">
              <option value="">全部地点</option>
              <option v-for="loc in filterOptions.locations" :key="loc" :value="loc">{{ loc }}</option>
            </select>
            <select v-model="filters.subcategory" @change="onSubcategoryChange">
              <option value="">全部子类</option>
              <option v-for="sub in filterOptions.subcategories" :key="sub.id" :value="sub.name">
                {{ sub.name }}
              </option>
            </select>
          </div>
        </div>

        <!-- 第三级：设备参数筛选 -->
        <div class="filter-section">
          <span class="filter-label">设备参数：</span>
          <div class="filter-group">
            <select v-model="filters.chip" @change="onChipChange">
              <option value="">全部芯片</option>
              <option v-for="chip in filterOptions.chips" :key="chip" :value="chip">{{ chip }}</option>
            </select>
            <select v-model="filters.sensor" @change="onSensorChange">
              <option value="">全部Sensor</option>
              <option v-for="s in filterOptions.sensors" :key="s" :value="s">{{ s }}</option>
            </select>
            <select v-model="filters.focal_length" @change="onFocalLengthChange">
              <option value="">全部焦距</option>
              <option v-for="fl in filterOptions.focal_lengths" :key="fl" :value="fl">{{ fl }}</option>
            </select>
            <select v-model="filters.resolution" @change="onResolutionChange">
              <option value="">全部分辨率</option>
              <option v-for="r in filterOptions.resolutions" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
        </div>

        <button class="btn-text" @click="resetFilters">重置筛选</button>
      </div>

      <!-- 排行榜图表 -->
      <div class="chart-panel">
        <div ref="barChartRef" class="chart-container"></div>
      </div>

      <!-- 排行榜表格（分页） -->
      <div class="table-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th>排名</th>
              <th>设备名</th>
              <th>主芯片</th>
              <th>Sensor</th>
              <th>焦距</th>
              <th>分辨率</th>
              <th>综合得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paginatedLeaderboard" :key="item.device_id">
              <td>{{ item.rank }}</td>
              <td>{{ item.device_name }}</td>
              <td>{{ item.main_chip }}</td>
              <td>{{ item.sensor_model }}</td>
              <td>{{ item.focal_length }}</td>
              <td>{{ item.resolution }}</td>
              <td class="score-cell">
                <div class="score-bar" :style="{ width: (item.bt_score / maxScore * 100) + '%' }"></div>
                <span>{{ filters.score_type === 'mean' ? item.mean_score?.toFixed(1) : item.bt_score?.toFixed(1) }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页控件 -->
        <div class="pagination">
          <div class="page-info">
            共 {{ leaderboard.length }} 条记录
            <select v-model.number="pageSize" @change="currentPage = 1">
              <option :value="10">每页 10 条</option>
              <option :value="20">每页 20 条</option>
              <option :value="50">每页 50 条</option>
              <option :value="100">每页 100 条</option>
            </select>
          </div>
          <div class="page-buttons">
            <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
            <span>{{ currentPage }} / {{ totalPages }}</span>
            <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
          </div>
        </div>
      </div>

      <!-- 雷达图 -->
      <div class="chart-panel">
        <h3>分场景得分对比</h3>
        <div ref="radarChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Tab 2: 详细数据（管理员可见） -->
    <div v-if="activeTab === 'detail' && authStore.isAdmin">
      <!-- 维度选择 + 导出按钮 -->
      <div class="detail-header">
        <div class="detail-tabs">
          <button :class="{ active: detailView === 'scene' }" @click="detailView = 'scene'">按场景</button>
          <button :class="{ active: detailView === 'user' }" @click="detailView = 'user'">按用户</button>
          <button :class="{ active: detailView === 'device' }" @click="detailView = 'device'">按设备</button>
        </div>
        <div class="export-buttons">
          <button class="btn-export" @click="exportRanking">导出排行榜</button>
          <button class="btn-export" @click="exportDetail">导出详细数据</button>
        </div>
      </div>

      <!-- 按场景查看 -->
      <div v-if="detailView === 'scene'" class="detail-panel">
        <div class="detail-selector">
          <label>场景：</label>
          <select v-model="selectedSceneId" @change="fetchSceneDetail">
            <option value="">请选择场景</option>
            <option v-for="scene in filterOptions.scenes" :key="scene.id" :value="scene.id">
              {{ scene.name }}
            </option>
          </select>
        </div>

        <div v-if="sceneDetail" class="detail-content">
          <!-- 场景统计 -->
          <div class="stats-row">
            <div class="stat-item">
              <span class="stat-value">{{ sceneDetail.scene?.total_records }}</span>
              <span class="stat-label">总记录</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-green">{{ sceneDetail.scene?.valid_records }}</span>
              <span class="stat-label">有效记录</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-red">{{ sceneDetail.scene?.invalid_records }}</span>
              <span class="stat-label">剔除记录</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-red">{{ sceneDetail.scene?.invalid_users?.length || 0 }}</span>
              <span class="stat-label">剔除用户</span>
            </div>
          </div>

          <!-- 剔除用户列表 -->
          <div v-if="sceneDetail.scene?.invalid_users?.length" class="invalid-users-card">
            <span class="label">剔除用户：</span>
            <span class="users-list">
              <span v-for="u in sceneDetail.scene.invalid_users" :key="u.id" class="user-tag">
                {{ u.display_name || u.username }}
              </span>
            </span>
          </div>

          <!-- 设备排行 -->
          <table class="data-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>设备名</th>
                <th>评测次数</th>
                <th>评分均值</th>
                <th>BT强度</th>
                <th>BT排名</th>
                <th>均值排名</th>
                <th>排名差</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sceneDetail.device_ranking" :key="item.device_id">
                <td>{{ item.rank }}</td>
                <td>{{ item.device_name }}</td>
                <td>{{ item.eval_count }}</td>
                <td>{{ item.mean_score?.toFixed(1) }}</td>
                <td>{{ item.bt_strength?.toFixed(2) }}</td>
                <td>{{ item.bt_rank }}</td>
                <td>{{ item.mean_rank }}</td>
                <td>
                  <span :class="item.rank_diff > 0 ? 'text-green' : item.rank_diff < 0 ? 'text-red' : ''">
                    {{ item.rank_diff > 0 ? '+' : '' }}{{ item.rank_diff }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按用户查看 -->
      <div v-if="detailView === 'user'" class="detail-panel">
        <div class="detail-selector">
          <label>用户：</label>
          <select v-model="selectedUserId" @change="fetchUserDetail">
            <option value="">请选择用户</option>
            <option v-for="user in usersList" :key="user.id" :value="user.id">
              {{ user.display_name || user.username }}
            </option>
          </select>
        </div>

        <div v-if="userDetail" class="detail-content">
          <!-- 用户统计 - 横向展示 -->
          <div class="stats-row">
            <div class="stat-item">
              <span class="stat-value">{{ userDetail.user?.total_evals }}</span>
              <span class="stat-label">总评测数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ userDetail.user?.first_evals }}</span>
              <span class="stat-label">首次评测</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ userDetail.user?.retest_evals }}</span>
              <span class="stat-label">重测数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ (userDetail.user?.retest_rate * 100)?.toFixed(0) }}%</span>
              <span class="stat-label">重测率</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-green">{{ userDetail.user?.passed_scenes }}</span>
              <span class="stat-label">通过场景</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-red">{{ userDetail.user?.rejected_scenes }}</span>
              <span class="stat-label">拒绝场景</span>
            </div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>场景</th>
                <th>评测对数</th>
                <th>一致性得分</th>
                <th>阈值</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="detail in userDetail.scene_details" :key="detail.scene_id">
                <td>{{ detail.scene_name }}</td>
                <td>{{ detail.eval_count }}</td>
                <td>{{ detail.retest_agreement_score?.toFixed(2) }}</td>
                <td>{{ detail.retest_agreement_threshold?.toFixed(2) }}</td>
                <td>
                  <span :class="detail.passed ? 'status-pass' : 'status-reject'">
                    {{ detail.passed ? '✓ 通过' : '✗ 拒绝' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按设备查看 -->
      <div v-if="detailView === 'device'" class="detail-panel">
        <div class="detail-selector">
          <label>设备：</label>
          <select v-model="selectedDeviceId" @change="fetchDeviceDetail">
            <option value="">请选择设备</option>
            <option v-for="item in allDevices" :key="item.device_id" :value="item.device_id">
              {{ item.device_name }}
            </option>
          </select>
        </div>

        <div v-if="deviceDetail" class="detail-content">
          <table class="data-table">
            <thead>
              <tr>
                <th>场景</th>
                <th>BT得分</th>
                <th>评分均值</th>
                <th>评测次数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="scene in deviceDetail.scenes" :key="scene.scene_id">
                <td>{{ scene.scene_name }}</td>
                <td>{{ scene.bt_score?.toFixed(1) }}</td>
                <td>{{ scene.mean_score?.toFixed(1) }}</td>
                <td>{{ scene.eval_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetLeaderboard, apiGetLeaderboardFilters, apiGetLeaderboardDetails, apiGetLeaderboardUsers, apiExportLeaderboard } from '../../api/index.js'
import * as echarts from 'echarts'

const authStore = useAuthStore()

const activeTab = ref('ranking')
const detailView = ref('scene')
const leaderboard = ref([])
const allDevices = ref([])
const filterOptions = ref({ categories: [], subcategories: [], scenes: [], locations: [], chips: [], sensors: [], focal_lengths: [], resolutions: [] })
const usersList = ref([])
const lastUpdated = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

const filters = ref({
  score_type: 'bt',
  scene: '',
  category: '',
  location: '',
  subcategory: '',
  chip: '',
  sensor: '',
  focal_length: '',
  resolution: '',
})

const selectedSceneId = ref(null)
const selectedUserId = ref(null)
const selectedDeviceId = ref(null)
const sceneDetail = ref(null)
const userDetail = ref(null)
const deviceDetail = ref(null)

const barChartRef = ref(null)
const radarChartRef = ref(null)
let barChart = null
let radarChart = null

const maxScore = computed(() => {
  if (!leaderboard.value.length) return 100
  return Math.max(...leaderboard.value.map(i => i.bt_score || 0))
})

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(leaderboard.value.length / pageSize.value))
})

const paginatedLeaderboard = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return leaderboard.value.slice(start, start + pageSize.value)
})

function resetFilters() {
  filters.value = {
    score_type: 'bt',
    scene: '',
    category: '',
    location: '',
    subcategory: '',
    chip: '',
    sensor: '',
    focal_length: '',
    resolution: '',
  }
  currentPage.value = 1
  fetchLeaderboard()
}

function getFilterParams() {
  const f = filters.value
  if (f.scene) {
    const [type, value] = f.scene.split(':')
    return { filter_type: type, filter_value: value, score_type: f.score_type }
  }
  if (f.category) return { filter_type: 'category', filter_value: f.category, score_type: f.score_type }
  if (f.location) return { filter_type: 'location', filter_value: f.location, score_type: f.score_type }
  if (f.subcategory) return { filter_type: 'subcategory', filter_value: f.subcategory, score_type: f.score_type }
  if (f.chip) return { filter_type: 'chip', filter_value: f.chip, score_type: f.score_type }
  if (f.sensor) return { filter_type: 'sensor', filter_value: f.sensor, score_type: f.score_type }
  if (f.focal_length) return { filter_type: 'focal_length', filter_value: f.focal_length, score_type: f.score_type }
  if (f.resolution) return { filter_type: 'resolution', filter_value: f.resolution, score_type: f.score_type }
  return { filter_type: 'overall', score_type: f.score_type }
}

async function fetchLeaderboard() {
  try {
    const params = getFilterParams()
    const resp = await apiGetLeaderboard(params)
    leaderboard.value = resp.data?.ranking || []
    allDevices.value = resp.data?.ranking || []
    lastUpdated.value = resp.data?.last_updated
    currentPage.value = 1
    await nextTick()
    renderBarChart()
    renderRadarChart()
  } catch (e) {
    console.error('获取排行榜失败:', e)
  }
}

async function fetchFilters() {
  try {
    const resp = await apiGetLeaderboardFilters()
    filterOptions.value = resp.data || {}
  } catch (e) {
    console.error('获取筛选选项失败:', e)
  }
}

async function fetchUsers() {
  try {
    const resp = await apiGetLeaderboardUsers()
    usersList.value = resp.data || []
  } catch (e) {
    console.error('获取用户列表失败:', e)
  }
}

function onSceneChange() { filters.value.category = ''; filters.value.location = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onCategoryChange() { filters.value.scene = ''; filters.value.location = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onLocationChange() { filters.value.scene = ''; filters.value.category = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onSubcategoryChange() { filters.value.scene = ''; filters.value.category = ''; filters.value.location = ''; fetchLeaderboard() }
function onChipChange() { fetchLeaderboard() }
function onSensorChange() { fetchLeaderboard() }
function onFocalLengthChange() { fetchLeaderboard() }
function onResolutionChange() { fetchLeaderboard() }

async function fetchSceneDetail() {
  if (!selectedSceneId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'scene', id: selectedSceneId.value })
    sceneDetail.value = resp.data
  } catch (e) {
    console.error('获取场景详情失败:', e)
  }
}

async function fetchUserDetail() {
  if (!selectedUserId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'user', id: selectedUserId.value })
    userDetail.value = resp.data
  } catch (e) {
    console.error('获取用户详情失败:', e)
  }
}

async function fetchDeviceDetail() {
  if (!selectedDeviceId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'device', id: selectedDeviceId.value })
    deviceDetail.value = resp.data
  } catch (e) {
    console.error('获取设备详情失败:', e)
  }
}

function exportRanking() {
  const params = getFilterParams()
  apiExportLeaderboard({ export_type: 'ranking', ...params })
}

function exportDetail() {
  const params = getFilterParams()
  apiExportLeaderboard({ export_type: 'detail', view_type: detailView.value, ...params })
}

function renderBarChart() {
  if (!barChartRef.value || !leaderboard.value.length) return
  if (!barChart) barChart = echarts.init(barChartRef.value)

  const top10 = leaderboard.value.slice(0, 10).reverse()
  barChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: top10.map(i => i.device_name),
    },
    series: [{
      type: 'bar',
      data: top10.map(i => ({
        value: filters.value.score_type === 'mean' ? i.mean_score : i.bt_score,
        itemStyle: { color: '#3b82f6' },
      })),
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  })
}

function renderRadarChart() {
  if (!radarChartRef.value || !leaderboard.value.length) return
  if (!radarChart) radarChart = echarts.init(radarChartRef.value)

  const top3 = leaderboard.value.slice(0, 3)
  const sceneNames = new Set()
  top3.forEach(item => {
    Object.keys(item.scene_scores || {}).forEach(name => sceneNames.add(name))
  })
  const indicators = [...sceneNames].map(name => ({ name, max: 100 }))

  radarChart.setOption({
    tooltip: {},
    legend: { data: top3.map(i => i.device_name) },
    radar: { indicator: indicators },
    series: [{
      type: 'radar',
      data: top3.map(item => ({
        name: item.device_name,
        value: [...sceneNames].map(name => item.scene_scores?.[name]?.bt_score || 0),
      })),
    }],
  })
}

watch(activeTab, (tab) => {
  if (tab === 'ranking') {
    nextTick(() => {
      barChart?.resize()
      radarChart?.resize()
    })
  }
})

onMounted(() => {
  fetchFilters()
  fetchLeaderboard()
  fetchUsers()

  window.addEventListener('resize', () => {
    barChart?.resize()
    radarChart?.resize()
  })
})
</script>

<style scoped>
.leaderboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tabs button {
  padding: 10px 24px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.tabs button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* 筛选面板 */
.filter-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.filter-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-section:last-of-type {
  margin-bottom: 8px;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  min-width: 80px;
  white-space: nowrap;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.filter-group select {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  min-width: 120px;
  background: white;
}

.filter-group button {
  padding: 6px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-group button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.btn-text {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 13px;
  padding: 4px 0;
}

.btn-text:hover {
  text-decoration: underline;
}

/* 图表 */
.chart-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-panel h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.chart-container {
  width: 100%;
  height: 400px;
}

/* 表格 */
.table-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.data-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #374151;
}

.data-table td {
  color: #475569;
}

.score-cell {
  position: relative;
  min-width: 120px;
}

.score-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 8px;
  background: #3b82f6;
  border-radius: 4px;
  opacity: 0.3;
}

.score-cell span {
  position: relative;
  font-weight: 600;
  color: #1e40af;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #64748b;
}

.page-info select {
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 13px;
}

.page-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-buttons button {
  padding: 6px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
}

.page-buttons button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-buttons span {
  font-size: 13px;
  color: #64748b;
}

/* 详细数据 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.detail-tabs {
  display: flex;
  gap: 8px;
}

.detail-tabs button {
  padding: 8px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.detail-tabs button.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #3b82f6;
}

.export-buttons {
  display: flex;
  gap: 8px;
}

.btn-export {
  padding: 6px 14px;
  background: white;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-export:hover {
  background: #eff6ff;
}

.detail-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.detail-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-selector label {
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.detail-selector select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  min-width: 200px;
}

/* 统计行 */
.stats-row {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #1e40af;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.text-green { color: #16a34a; }
.text-red { color: #dc2626; }

/* 剔除用户 */
.invalid-users-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 13px;
}

.invalid-users-card .label {
  color: #64748b;
  white-space: nowrap;
}

.users-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.user-tag {
  padding: 2px 8px;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 4px;
  font-size: 12px;
}

.status-pass {
  color: #16a34a;
  font-weight: 600;
}

.status-reject {
  color: #dc2626;
  font-weight: 600;
}

@media (max-width: 768px) {
  .filter-section {
    flex-direction: column;
    align-items: flex-start;
  }
  .filter-group {
    width: 100%;
  }
  .chart-container {
    height: 300px;
  }
  .detail-header {
    flex-direction: column;
    gap: 12px;
  }
  .stats-row {
    flex-wrap: wrap;
    gap: 16px;
  }
}
</style>
