<template>
  <div class="cleaning-page">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">数据清洗</h1>
        <button class="btn-help" @click="showHelpModal = true" title="查看清洗流程说明">?</button>
      </div>
      <div class="header-right">
        <button class="btn-primary" @click="runCleaning" :disabled="cleaning">
          {{ cleaning ? '清洗中...' : '执行清洗' }}
        </button>
      </div>
    </div>

    <!-- 清洗状态统计 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">总 Session</div>
      </div>
      <div class="stat-card valid">
        <div class="stat-value">{{ stats.valid }}</div>
        <div class="stat-label">有效</div>
      </div>
      <div class="stat-card invalid">
        <div class="stat-value">{{ stats.invalid }}</div>
        <div class="stat-label">无效</div>
      </div>
      <div class="stat-card pending">
        <div class="stat-value">{{ stats.pending }}</div>
        <div class="stat-label">待处理</div>
      </div>
    </div>

    <!-- 清洗结果提示 -->
    <div v-if="cleaningResult" class="result-message" :class="cleaningResult.success ? 'success' : 'warning'">
      <span>{{ cleaningResult.message }}</span>
      <button class="btn-close-msg" @click="cleaningResult = null">&times;</button>
    </div>

    <!-- 第一层清洗结果：Session 列表 -->
    <div class="section">
      <h2 class="section-title">第一层清洗结果 <span class="section-subtitle">Session 级别</span></h2>
      <div class="table-section">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户</th>
              <th>状态</th>
              <th>
                重测信度
                <span class="tooltip-icon" title="重复图对评分一致率，≥0.6 通过">ⓘ</span>
              </th>
              <th>
                熵权重
                <span class="tooltip-icon" title="评分分布多样性系数，≥1.0 为满权重">ⓘ</span>
              </th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in details" :key="item.session_id">
              <td>{{ item.session_id }}</td>
              <td>{{ item.username }}</td>
              <td>
                <span class="status-tag" :class="item.session_status">
                  {{ item.session_status }}
                </span>
              </td>
              <td>{{ item.retest_weight?.toFixed(2) ?? '-' }}</td>
              <td>{{ item.entropy_weight?.toFixed(2) ?? '-' }}</td>
              <td>
                <button class="btn-sm" @click="showDetail(item)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 第二层清洗结果：用户一致率 -->
    <div class="section">
      <h2 class="section-title">第二层清洗结果 <span class="section-subtitle">用户级别</span></h2>
      <div class="table-section">
        <table class="data-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>
                一致率
                <span class="tooltip-icon" title="用户评分与群体共识的一致程度，≥0.5 通过">ⓘ</span>
              </th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in userAgreements" :key="item.user_id">
              <td>{{ item.username }}</td>
              <td>{{ item.agreement?.toFixed(2) ?? '-' }}</td>
              <td>
                <span class="status-tag" :class="item.status">
                  {{ item.status }}
                </span>
              </td>
            </tr>
            <tr v-if="!userAgreements.length">
              <td colspan="3" class="empty-row">暂无数据，请先执行清洗</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 清洗流程说明弹窗 -->
    <div v-if="showHelpModal" class="modal-overlay" @click.self="showHelpModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>数据清洗流程说明</h3>
          <button class="btn-close" @click="showHelpModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="help-section">
            <h4>第一层清洗（自动）</h4>
            <p class="help-trigger">触发时机：用户提交评测轮次后自动执行</p>
            <div class="help-content">
              <p><strong>检查项：</strong></p>
              <ol>
                <li>
                  <strong>熵检查</strong>：评分分布的信息熵，衡量评分多样性
                  <ul>
                    <li>熵 = 0：所有评分相同，Session 无效</li>
                    <li>熵 ≥ 1.0：满权重</li>
                  </ul>
                </li>
                <li>
                  <strong>重测信度</strong>：重复图对的评分一致率
                  <ul>
                    <li>一致率 ≥ 0.6：通过</li>
                    <li>一致率 < 0.6：Session 无效</li>
                  </ul>
                </li>
              </ol>
            </div>
          </div>

          <div class="help-section">
            <h4>第二层清洗（手动）</h4>
            <p class="help-trigger">触发时机：管理员点击「执行清洗」</p>
            <div class="help-content">
              <p><strong>检查项：</strong></p>
              <ol>
                <li>
                  <strong>群体一致率</strong>：用户评分与群体共识的一致程度
                  <ul>
                    <li>使用 Leave-One-Out 方法计算</li>
                    <li>一致率 ≥ 0.5：通过，计算用户权重</li>
                    <li>一致率 < 0.5：用户评测无效</li>
                  </ul>
                </li>
              </ol>
            </div>
          </div>

          <div class="help-section">
            <h4>权重计算</h4>
            <div class="help-content">
              <p><strong>最终权重 = 重测信度 × 熵权重 × 一致率</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Session 详情弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Session #{{ modalData.session_id }} 详情 - {{ modalData.username }}</h3>
          <button class="btn-close" @click="showModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="weight-info">
            <h4>权重信息</h4>
            <div class="weight-grid">
              <div class="weight-item">
                <span class="weight-label">重测信度</span>
                <span class="weight-value">{{ modalData.retest_weight?.toFixed(2) }}</span>
              </div>
              <div class="weight-item">
                <span class="weight-label">熵权重</span>
                <span class="weight-value">{{ modalData.entropy_weight?.toFixed(2) }}</span>
              </div>
              <div class="weight-item">
                <span class="weight-label">最终权重</span>
                <span class="weight-value">{{ finalWeight }}</span>
              </div>
            </div>
          </div>

          <div class="pair-info">
            <h4>Pair 评测详情</h4>
            <table class="data-table">
              <thead>
                <tr>
                  <th>PairID</th>
                  <th>设备A</th>
                  <th>设备B</th>
                  <th>评分</th>
                  <th>方向</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pair in modalData.pairs" :key="pair.pair_id">
                  <td>{{ pair.pair_id }}</td>
                  <td>{{ pair.device_a_name }}</td>
                  <td>{{ pair.device_b_name }}</td>
                  <td>{{ pair.score }}</td>
                  <td>{{ pair.direction }}</td>
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
import { apiGetRankingReport, apiGetSessionPairs, apiRunCleaning } from '../../api/index.js'

const cleaning = ref(false)
const stats = ref({ total: 0, valid: 0, invalid: 0, pending: 0 })
const details = ref([])
const userAgreements = ref([])
const showModal = ref(false)
const showHelpModal = ref(false)
const modalData = ref({})
const cleaningResult = ref(null)

const finalWeight = computed(() => {
  if (!modalData.value.retest_weight || !modalData.value.entropy_weight) return '-'
  return (modalData.value.retest_weight * modalData.value.entropy_weight).toFixed(2)
})

async function fetchReport() {
  try {
    const data = await apiGetRankingReport()
    stats.value = {
      total: data.total_sessions,
      valid: data.valid_sessions,
      invalid: data.invalid_sessions,
      pending: data.pending_sessions,
    }
    details.value = (data.details || []).map(d => ({ ...d, expanded: false }))
    userAgreements.value = data.user_agreements || []
  } catch (e) {
    console.error('Failed to fetch report:', e)
  }
}

async function runCleaning() {
  cleaning.value = true
  cleaningResult.value = null
  try {
    const result = await apiRunCleaning()
    await fetchReport()

    if (result.success) {
      if (result.reason) {
        const layer2Reason = result.layer2?.reason || ''
        cleaningResult.value = {
          success: false,
          message: `清洗完成，但无有效评测数据。${layer2Reason}`
        }
      } else if (result.ranking_saved > 0) {
        cleaningResult.value = {
          success: true,
          message: `清洗完成！已生成排行榜：${result.device_count} 个设备，${result.ranking_saved} 条排名记录`
        }
      } else {
        cleaningResult.value = {
          success: true,
          message: '清洗流程执行完成'
        }
      }
    }
  } catch (e) {
    console.error('Failed to run cleaning:', e)
    cleaningResult.value = {
      success: false,
      message: '清洗失败：' + (e.message || '未知错误')
    }
  } finally {
    cleaning.value = false
  }
}

async function showDetail(item) {
  try {
    const data = await apiGetSessionPairs(item.session_id)
    modalData.value = data
    showModal.value = true
  } catch (e) {
    console.error('Failed to fetch session pairs:', e)
  }
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
.cleaning-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin: 0;
}

.btn-help {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  color: #3b82f6;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-help:hover {
  background: #dbeafe;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-card.valid { border-left: 4px solid #22c55e; }
.stat-card.invalid { border-left: 4px solid #ef4444; }
.stat-card.pending { border-left: 4px solid #f59e0b; }

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1e40af;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 4px;
}

.result-message {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 14px;
}

.result-message.success {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #16a34a;
}

.result-message.warning {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #d97706;
}

.btn-close-msg {
  background: none;
  border: none;
  font-size: 18px;
  color: inherit;
  cursor: pointer;
  opacity: 0.7;
}

.btn-close-msg:hover { opacity: 1; }

.section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-subtitle {
  font-size: 13px;
  font-weight: 400;
  color: #94a3b8;
}

.table-section {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 12px 16px;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.data-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
  cursor: help;
  margin-left: 4px;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-tag.valid { background: #dcfce7; color: #16a34a; }
.status-tag.invalid { background: #fef2f2; color: #dc2626; }
.status-tag.pending { background: #fef3c7; color: #d97706; }

.btn-sm {
  padding: 4px 12px;
  background: #f0f5ff;
  border: 1px solid #dbeafe;
  border-radius: 4px;
  color: #3b82f6;
  font-size: 12px;
  cursor: pointer;
}

.btn-sm:hover { background: #dbeafe; }

.empty-row {
  text-align: center;
  color: #94a3b8;
  padding: 32px 16px;
}

.btn-primary {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Modal */
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
  margin: 0;
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

.weight-info, .pair-info {
  margin-bottom: 24px;
}

.weight-info h4, .pair-info h4 {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
}

.weight-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.weight-item {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.weight-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.weight-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
}

/* Help Modal */
.help-section {
  margin-bottom: 24px;
}

.help-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: #1e40af;
  margin-bottom: 8px;
}

.help-trigger {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
}

.help-content {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
}

.help-content p {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #334155;
}

.help-content ol {
  margin: 0;
  padding-left: 20px;
}

.help-content li {
  margin-bottom: 8px;
  font-size: 14px;
  color: #334155;
}

.help-content ul {
  margin: 4px 0 0 0;
  padding-left: 20px;
}

.help-content ul li {
  margin-bottom: 4px;
  font-size: 13px;
  color: #64748b;
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .weight-grid { grid-template-columns: 1fr; }
}
</style>
