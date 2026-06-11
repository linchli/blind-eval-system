<template>
  <div class="data-cleaning-page">
    <h1 class="page-title">🧹 数据清洗</h1>

    <div class="config-status-row">
      <div class="config-panel">
        <h3 class="panel-title">清洗参数配置</h3>
        <div class="param-item">
          <label>重测一致性阈值：</label>
          <input type="range" v-model.number="params.retest_agreement_threshold" min="0.50" max="0.90" step="0.01" />
          <span class="param-value">{{ params.retest_agreement_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>重测硬拒绝阈值：</label>
          <input type="range" v-model.number="params.retest_hard_reject_threshold" min="0.30" max="0.70" step="0.01" />
          <span class="param-value">{{ params.retest_hard_reject_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>用户组最大阈值：</label>
          <input type="range" v-model.number="params.group_max_threshold" min="0.60" max="1.00" step="0.01" />
          <span class="param-value">{{ params.group_max_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>复评比例要求：</label>
          <input type="range" v-model.number="retestRatioPercent" min="5" max="30" step="1" />
          <span class="param-value">{{ retestRatioPercent }}%</span>
        </div>
        <div class="param-item">
          <label>最小设备数：</label>
          <input type="range" v-model.number="params.min_devices_per_scene" min="2" max="10" step="1" />
          <span class="param-value">{{ params.min_devices_per_scene }}</span>
        </div>
        <button class="btn-text" @click="resetDefaults">恢复默认值</button>
      </div>

      <div class="status-panel">
        <h3 class="panel-title">清洗状态</h3>
        <div v-if="status.has_cleaned" class="status-info">
          <div class="status-section">
            <p><strong>清洗状态</strong></p>
            <p>最后清洗时间：{{ formatTime(status.last_cleaned_at) }}</p>
            <p>已清洗评测数：{{ status.cleaned_record_count }}</p>
          </div>
          <div class="status-divider"></div>
          <div class="status-section">
            <p><strong>当前评测统计</strong></p>
            <p>评测总数：{{ status.debug_total_count || 0 }}</p>
            <p>已提交评测数：{{ status.current_record_count }}</p>
            <p>草稿评测数：{{ status.debug_draft_count || 0 }}</p>
          </div>
          <p v-if="status.needs_refresh" class="warning">⚠️ 有 {{ status.new_record_count }} 条新评测待清洗</p>
        </div>
        <div v-else class="status-info">
          <p>尚未执行过清洗</p>
        </div>
      </div>
    </div>

    <div class="action-bar">
      <button class="btn-primary" @click="executeCleaning" :disabled="cleaning">
        {{ cleaning ? '清洗中...' : '执行数据清洗' }}
      </button>
      <button class="btn-outline" @click="exportReport" :disabled="!status.has_cleaned">
        导出清洗报告
      </button>
    </div>

    <div v-if="result" class="result-section">
      <div class="result-summary">
        <span>总评测数：{{ result.total_records }}</span>
        <span>有效评测：{{ result.valid_records }}</span>
        <span>无效评测：{{ result.invalid_records }}</span>
      </div>

      <div class="result-table-section">
        <h3>单用户一致性检验（重测信度）</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th class="filterable" @click.stop="toggleFilter('singleUser', 'user')">
                用户
                <span class="filter-icon" :class="{ active: singleUserFilter.user }">▼</span>
                <div v-if="activeFilter.singleUser === 'user'" class="filter-dropdown" @click.stop>
                  <input v-model="singleUserSearch.user" placeholder="搜索..." class="filter-search" />
                  <div class="filter-list">
                    <div class="filter-option" :class="{ selected: !singleUserFilter.user }" @click="setFilter('singleUser', 'user', '')">全部</div>
                    <div v-for="val in filteredUserOptions" :key="val" class="filter-option" :class="{ selected: singleUserFilter.user === val }" @click="setFilter('singleUser', 'user', val)">{{ val }}</div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click.stop="toggleFilter('singleUser', 'scene')">
                场景
                <span class="filter-icon" :class="{ active: singleUserFilter.scene }">▼</span>
                <div v-if="activeFilter.singleUser === 'scene'" class="filter-dropdown" @click.stop>
                  <input v-model="singleUserSearch.scene" placeholder="搜索..." class="filter-search" />
                  <div class="filter-list">
                    <div class="filter-option" :class="{ selected: !singleUserFilter.scene }" @click="setFilter('singleUser', 'scene', '')">全部</div>
                    <div v-for="val in filteredSceneOptions" :key="val" class="filter-option" :class="{ selected: singleUserFilter.scene === val }" @click="setFilter('singleUser', 'scene', val)">{{ val }}</div>
                  </div>
                </div>
              </th>
              <th>一致性得分</th>
              <th>阈值</th>
              <th>状态</th>
              <th>重测对数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in paginatedSingleUserRows" :key="idx">
              <td>{{ row.user_name }}</td>
              <td>{{ row.scene_name }}</td>
              <td>{{ row.retest_agreement_score?.toFixed(2) }}</td>
              <td>{{ row.retest_agreement_threshold?.toFixed(2) }}</td>
              <td>
                <span :class="row.rejected ? 'status-reject' : 'status-pass'">
                  {{ row.rejected ? '✗' : '✓' }}
                </span>
              </td>
              <td>{{ row.retest_matched_pairs }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <div class="page-size">
            <label>每页</label>
            <select v-model.number="singleUserPageSize" @change="singleUserPage = 1">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
            <label>条</label>
          </div>
          <span class="page-info">共 {{ filteredSingleUserRows.length }} 条，{{ singleUserPage }}/{{ singleUserTotalPages }} 页</span>
          <div class="page-btns">
            <button :disabled="singleUserPage <= 1" @click="singleUserPage--">上一页</button>
            <button :disabled="singleUserPage >= singleUserTotalPages" @click="singleUserPage++">下一页</button>
          </div>
        </div>
      </div>

      <div class="result-table-section">
        <h3>用户组一致性检验</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th class="filterable" @click.stop="toggleFilter('userGroup', 'scene')">
                场景
                <span class="filter-icon" :class="{ active: userGroupFilter.scene }">▼</span>
                <div v-if="activeFilter.userGroup === 'scene'" class="filter-dropdown" @click.stop>
                  <input v-model="userGroupSearch.scene" placeholder="搜索..." class="filter-search" />
                  <div class="filter-list">
                    <div class="filter-option" :class="{ selected: !userGroupFilter.scene }" @click="setFilter('userGroup', 'scene', '')">全部</div>
                    <div v-for="val in filteredUserGroupSceneOptions" :key="val" class="filter-option" :class="{ selected: userGroupFilter.scene === val }" @click="setFilter('userGroup', 'scene', val)">{{ val }}</div>
                  </div>
                </div>
              </th>
              <th>参评用户数</th>
              <th>通过</th>
              <th>拒绝</th>
              <th>通过率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in paginatedUserGroupRows" :key="idx">
              <td>{{ row.scene_name }}</td>
              <td>{{ row.total_user_scenes }}</td>
              <td>{{ row.passed }}</td>
              <td>{{ row.rejected }}</td>
              <td>{{ row.pass_rate }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <div class="page-size">
            <label>每页</label>
            <select v-model.number="userGroupPageSize" @change="userGroupPage = 1">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
            <label>条</label>
          </div>
          <span class="page-info">共 {{ filteredUserGroupRows.length }} 条，{{ userGroupPage }}/{{ userGroupTotalPages }} 页</span>
          <div class="page-btns">
            <button :disabled="userGroupPage <= 1" @click="userGroupPage--">上一页</button>
            <button :disabled="userGroupPage >= userGroupTotalPages" @click="userGroupPage++">下一页</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiGetCleaningDefaults, apiGetCleaningStatus, apiExecuteCleaning, apiExportCleaningReport } from '../../api/index.js'

const defaultParams = {
  retest_agreement_threshold: 0.70,
  retest_hard_reject_threshold: 0.55,
  group_max_threshold: 0.85,
  retest_ratio: 0.10,
  min_devices_per_scene: 2,
}

const params = ref({ ...defaultParams })
const status = ref({})
const result = ref(null)
const cleaning = ref(false)

// 分页和筛选状态
const activeFilter = ref({ singleUser: null, userGroup: null })

// 单用户一致性检验
const singleUserFilter = ref({ user: '', scene: '' })
const singleUserSearch = ref({ user: '', scene: '' })
const singleUserPage = ref(1)
const singleUserPageSize = ref(10)

// 用户组一致性检验
const userGroupFilter = ref({ scene: '' })
const userGroupSearch = ref({ scene: '' })
const userGroupPage = ref(1)
const userGroupPageSize = ref(10)

// 从 sessionStorage 恢复清洗结果
const cachedResult = sessionStorage.getItem('cleaning_result')
if (cachedResult) {
  try {
    result.value = JSON.parse(cachedResult)
  } catch (e) {
    sessionStorage.removeItem('cleaning_result')
  }
}

const retestRatioPercent = computed({
  get: () => Math.round(params.value.retest_ratio * 100),
  set: (v) => { params.value.retest_ratio = v / 100 },
})

// 切换筛选下拉框
function toggleFilter(table, column) {
  if (activeFilter.value[table] === column) {
    activeFilter.value[table] = null
  } else {
    activeFilter.value[table] = column
  }
}

// 设置筛选值
function setFilter(table, column, value) {
  if (table === 'singleUser') {
    singleUserFilter.value[column] = value
    singleUserPage.value = 1
  } else {
    userGroupFilter.value[column] = value
    userGroupPage.value = 1
  }
  activeFilter.value[table] = null
}

// 点击外部关闭下拉框
function closeAllFilters() {
  activeFilter.value = { singleUser: null, userGroup: null }
}

// 单用户一致性检验 - 扁平化数据
const singleUserRows = computed(() => {
  if (!result.value?.single_user_details) return []
  const rows = []
  for (const [userId, data] of Object.entries(result.value.single_user_details)) {
    for (const detail of data.scene_details || []) {
      rows.push({
        user_name: data.user_name || userId,
        scene_name: detail.scene_name || '',
        retest_agreement_score: detail.retest_agreement_score,
        retest_agreement_threshold: detail.retest_agreement_threshold,
        rejected: detail.rejected,
        retest_matched_pairs: detail.retest_matched_pairs,
      })
    }
  }
  return rows
})

// 单用户 - 唯一值列表
const uniqueUserNames = computed(() => [...new Set(singleUserRows.value.map(r => r.user_name))].sort())
const uniqueSceneNames = computed(() => [...new Set(singleUserRows.value.map(r => r.scene_name))].sort())

// 单用户 - 搜索过滤后的选项
const filteredUserOptions = computed(() => {
  const search = singleUserSearch.value.user.toLowerCase()
  if (!search) return uniqueUserNames.value
  return uniqueUserNames.value.filter(v => v.toLowerCase().includes(search))
})
const filteredSceneOptions = computed(() => {
  const search = singleUserSearch.value.scene.toLowerCase()
  if (!search) return uniqueSceneNames.value
  return uniqueSceneNames.value.filter(v => v.toLowerCase().includes(search))
})

// 单用户 - 筛选
const filteredSingleUserRows = computed(() => {
  const user = singleUserFilter.value.user
  const scene = singleUserFilter.value.scene
  return singleUserRows.value.filter(row => {
    if (user && row.user_name !== user) return false
    if (scene && row.scene_name !== scene) return false
    return true
  })
})

// 单用户 - 分页
const singleUserTotalPages = computed(() => Math.max(1, Math.ceil(filteredSingleUserRows.value.length / singleUserPageSize.value)))
const paginatedSingleUserRows = computed(() => {
  const start = (singleUserPage.value - 1) * singleUserPageSize.value
  return filteredSingleUserRows.value.slice(start, start + singleUserPageSize.value)
})

// 用户组一致性检验 - 扁平化数据
const userGroupRows = computed(() => {
  if (!result.value?.user_group_details) return []
  const rows = []
  for (const [sceneId, stats] of Object.entries(result.value.user_group_details)) {
    const total = stats.total_user_scenes || 0
    const passed = stats.passed || 0
    rows.push({
      scene_name: stats.scene_name || '',
      total_user_scenes: total,
      passed,
      rejected: stats.rejected || 0,
      pass_rate: total > 0 ? ((passed / total) * 100).toFixed(1) + '%' : '-',
    })
  }
  return rows
})

// 用户组 - 唯一值列表
const uniqueUserGroupSceneNames = computed(() => [...new Set(userGroupRows.value.map(r => r.scene_name))].sort())

// 用户组 - 搜索过滤后的选项
const filteredUserGroupSceneOptions = computed(() => {
  const search = userGroupSearch.value.scene.toLowerCase()
  if (!search) return uniqueUserGroupSceneNames.value
  return uniqueUserGroupSceneNames.value.filter(v => v.toLowerCase().includes(search))
})

// 用户组 - 筛选
const filteredUserGroupRows = computed(() => {
  const scene = userGroupFilter.value.scene
  return userGroupRows.value.filter(row => {
    if (scene && row.scene_name !== scene) return false
    return true
  })
})

// 用户组 - 分页
const userGroupTotalPages = computed(() => Math.max(1, Math.ceil(filteredUserGroupRows.value.length / userGroupPageSize.value)))
const paginatedUserGroupRows = computed(() => {
  const start = (userGroupPage.value - 1) * userGroupPageSize.value
  return filteredUserGroupRows.value.slice(start, start + userGroupPageSize.value)
})

function resetDefaults() {
  params.value = { ...defaultParams }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchStatus() {
  try {
    const resp = await apiGetCleaningStatus()
    status.value = resp.data || {}
  } catch (e) {
    console.error('获取清洗状态失败:', e)
  }
}

async function fetchDefaults() {
  try {
    const resp = await apiGetCleaningDefaults()
    if (resp.data) {
      params.value = { ...defaultParams, ...resp.data }
    }
  } catch (e) {
    console.error('获取默认参数失败:', e)
  }
}

async function executeCleaning() {
  if (!confirm('确定要执行数据清洗吗？')) return
  cleaning.value = true
  try {
    const resp = await apiExecuteCleaning(params.value)
    result.value = resp.data
    sessionStorage.setItem('cleaning_result', JSON.stringify(resp.data))
    window.showAdminToast?.('数据清洗完成', 'success')
    await fetchStatus()
  } catch (e) {
    window.showAdminToast?.('清洗失败: ' + e.message, 'error')
  } finally {
    cleaning.value = false
  }
}

function exportReport() {
  apiExportCleaningReport()
}

onMounted(() => {
  fetchDefaults()
  fetchStatus()
  // 点击外部关闭筛选下拉框
  document.addEventListener('click', closeAllFilters)
})
</script>

<style scoped>
.data-cleaning-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.config-status-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.config-panel, .status-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.param-item label {
  min-width: 140px;
  font-size: 14px;
  color: #475569;
}

.param-item input[type="range"] {
  flex: 1;
}

.param-value {
  min-width: 50px;
  text-align: right;
  font-weight: 600;
  color: #1e40af;
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

.status-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #475569;
}

.status-info .warning {
  color: #d97706;
  font-weight: 500;
}

.status-section p strong {
  color: #374151;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 12px 0;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.btn-primary {
  padding: 12px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline {
  padding: 12px 24px;
  background: white;
  color: #3b82f6;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover:not(:disabled) {
  background: #eff6ff;
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-summary {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-summary span {
  font-size: 14px;
  color: #475569;
}

.result-table-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-table-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
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

.status-pass {
  color: #16a34a;
  font-weight: 600;
}

.status-reject {
  color: #dc2626;
  font-weight: 600;
}

/* 列头筛选下拉框 */
.filterable {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.filter-icon {
  font-size: 10px;
  margin-left: 4px;
  color: #94a3b8;
  transition: color 0.15s;
}

.filter-icon.active {
  color: #3b82f6;
}

.filter-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 200px;
  max-height: 300px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.filter-search {
  padding: 8px 12px;
  border: none;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
  outline: none;
  border-radius: 8px 8px 0 0;
}

.filter-list {
  overflow-y: auto;
  max-height: 250px;
}

.filter-option {
  padding: 8px 12px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: background 0.1s;
}

.filter-option:hover {
  background: #f1f5f9;
}

.filter-option.selected {
  background: #eff6ff;
  color: #3b82f6;
  font-weight: 500;
}

/* 分页控件 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.page-size {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
}

.page-size select {
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 13px;
  background: white;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

.page-btns {
  display: flex;
  gap: 8px;
}

.page-btns button {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.page-btns button:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.page-btns button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .config-status-row {
    grid-template-columns: 1fr;
  }
  .action-bar {
    flex-direction: column;
  }
}
</style>
