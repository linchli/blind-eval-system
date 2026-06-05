<template>
  <div class="pair-manage-page">
    <h1 class="page-title">🔗 配对管理</h1>

    <div class="operation-section">
      <h4>操作区</h4>

      <div class="form-group">
        <label>选择场景</label>
        <select v-model="selectedSceneId" @change="fetchSceneStats" class="form-select">
          <option value="">请选择场景</option>
          <option v-for="scene in scenes" :key="scene.id" :value="scene.id">{{ scene.name }}</option>
        </select>
      </div>

      <div class="strategy-section">
        <div class="strategy-item">
          <input type="radio" id="strategy-full" value="full" v-model="pairStrategy" />
          <label for="strategy-full">全量配对</label>
        </div>
        <div class="strategy-item disabled">
          <input type="radio" id="strategy-baseline" value="baseline" v-model="pairStrategy" disabled />
          <label for="strategy-baseline" title="基准设备需根据排行榜给出，功能暂未开放">基准配对</label>
        </div>
      </div>

      <div class="form-group">
        <label>基准设备</label>
        <select v-model="baselineDeviceId" class="form-select" :disabled="pairStrategy === 'full'">
          <option value="">请选择</option>
          <option v-for="device in sceneDevices" :key="device.id" :value="device.id">{{ device.name }}</option>
        </select>
      </div>

      <button class="btn-primary btn-large" @click="openPreviewDialog" :disabled="!selectedSceneId || previewLoading">
        {{ previewLoading ? '计算中...' : '生成配对' }}
      </button>
    </div>

    <div v-if="sceneStats" class="scene-stats">
      <h4>当前场景统计</h4>
      <div class="stat-item">
        <span class="stat-label">图像数</span>
        <span class="stat-value">{{ sceneStats.image_count }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">已有配对</span>
        <span class="stat-value">{{ sceneStats.pair_count }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">可新增</span>
        <span class="stat-value">{{ previewData?.new_pair_count || 0 }}</span>
      </div>
    </div>

    <div class="pair-list-section">
      <h4>配对列表</h4>
      <div v-if="pairs.length === 0" class="empty-tip">
        暂无配对数据，请先生成配对
      </div>
      <div v-else class="pair-list">
        <div v-for="pair in pairs" :key="pair.id" class="pair-item">
          <span class="pair-index">#{{ pair.sort_order}}</span>
          <span class="pair-devices">
            {{ pair.device_a_name }} vs {{ pair.device_b_name }}
          </span>
          <span class="pair-eval">{{ pair.eval_count }}人已评价</span>
        </div>
      </div>
    </div>

    <!-- 预览确认对话框 -->
    <div v-if="showPreviewDialog" class="modal-overlay" @click.self="showPreviewDialog = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>确认生成配对</h2>
          <button class="btn-icon" @click="showPreviewDialog = false">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="previewLoading" class="loading-state">
            <div class="spinner"></div>
            <span>正在计算预检结果...</span>
          </div>

          <div v-else-if="previewData" class="preview-content">
            <p class="preview-item">当前场景：{{ previewData.scene_name }}</p>
            <p class="preview-item">配对策略：全量配对</p>

            <h4 class="section-title">── 预检计算结果 ───</h4>
            <div class="preview-stats">
              <div class="preview-stat">
                <span class="preview-label">当前图像数</span>
                <span class="preview-value">{{ previewData.current_image_count }}</span>
              </div>
              <div class="preview-stat">
                <span class="preview-label">理论全量配对</span>
                <span class="preview-value">C({{ previewData.current_image_count }},2) = {{ previewData.total_combinations }} 对</span>
              </div>
              <div class="preview-stat">
                <span class="preview-label">已有配对数</span>
                <span class="preview-value">{{ previewData.existing_pair_count }} 对</span>
              </div>
              <div class="preview-stat highlight">
                <span class="preview-label">预计新增配对</span>
                <span class="preview-value">{{ previewData.new_pair_count }} 对</span>
              </div>
            </div>

            <div class="warning-box">
              ⚠️ 新增配对将立即对评测员可见，确认生成？
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="showPreviewDialog = false">取消</button>
          <button class="btn-primary" @click="generatePairs" :disabled="generating || previewLoading">
            {{ generating ? '生成中...' : '确认生成' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'

const authStore = useAuthStore()

const scenes = ref([])
const pairs = ref([])
const selectedSceneId = ref('')
const pairStrategy = ref('full')
const baselineDeviceId = ref('')
const sceneStats = ref(null)
const sceneDevices = ref([])

const showPreviewDialog = ref(false)
const previewLoading = ref(false)
const generating = ref(false)
const previewData = ref(null)

async function fetchScenes() {
  try {
    const data = await fetch('/api/admin/scenes', {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    }).then(r => r.json())
    scenes.value = data
  } catch (e) {
    console.error('获取场景失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '获取场景失败', 'error')
  }
}

function openPreviewDialog() {
  showPreviewDialog.value = true
  fetchPreview()
}

async function fetchPairs() {
  try {
    const data = await fetch(`/api/admin/pairs?scene_id=${selectedSceneId.value}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    }).then(r => r.json())
    pairs.value = data
  } catch (e) {
    console.error('获取配对失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '获取配对失败', 'error')
  }
}

async function fetchSceneStats() {
  if (!selectedSceneId.value) {
    sceneStats.value = null
    pairs.value = []
    previewData.value = null
    return
  }

  try {
    const [stats, pairList, devicesList, preview] = await Promise.all([
      fetch(`/api/admin/pairs/scene-stats/${selectedSceneId.value}`, {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      }).then(r => r.json()),
      fetch(`/api/admin/pairs?scene_id=${selectedSceneId.value}`, {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      }).then(r => r.json()),
      fetch('/api/admin/devices', {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      }).then(r => r.json()),
      fetch('/api/admin/pairs/preview', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scene_id: Number(selectedSceneId.value),
          strategy: 'full',
        }),
      }).then(r => r.json()),
    ])
    sceneStats.value = stats
    pairs.value = pairList
    if (!preview.error) previewData.value = preview

    // 获取该场景的设备列表（用于基准配对）
    const sceneImages = await fetch(`/api/admin/images?scene_id=${selectedSceneId.value}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    }).then(r => r.json())
    const deviceIds = [...new Set(sceneImages.map(img => img.device_id))]
    sceneDevices.value = devicesList.filter(d => deviceIds.includes(d.id))
  } catch (e) {
    console.error('获取场景统计失败:', e)
  }
}

async function fetchPreview() {
  previewLoading.value = true
  previewData.value = null

  try {
    const data = await fetch('/api/admin/pairs/preview', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        scene_id: selectedSceneId.value,
        strategy: pairStrategy.value,
      }),
    }).then(r => r.json())
    previewData.value = data
  } catch (e) {
    console.error('预览失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '预览失败', 'error')
  } finally {
    previewLoading.value = false
  }
}

async function generatePairs() {
  if (!previewData.value || previewData.value.new_pair_count === 0) {
    showPreviewDialog.value = false
    return
  }

  generating.value = true

  try {
    const data = await fetch('/api/admin/pairs/generate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        scene_id: selectedSceneId.value,
        strategy: pairStrategy.value,
      }),
    }).then(r => r.json())

    if (window.showAdminToast) {
      window.showAdminToast(data.message || '配对生成成功', 'success')
    }
    showPreviewDialog.value = false
    await fetchSceneStats()
    await fetchPairs()
  } catch (e) {
    console.error('生成配对失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '生成配对失败', 'error')
  } finally {
    generating.value = false
  }
}

onMounted(() => {
  fetchScenes()
})
</script>

<style scoped>
.pair-manage-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.btn-primary, .btn-cancel {
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}

.btn-primary { background: #3b82f6; color: #fff; border: none; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary.btn-large {
  width: 100%; padding: 14px 24px; font-size: 16px;
}
.btn-cancel { background: #fff; color: #64748b; border: 1px solid #e2e8f0; }

.operation-section, .scene-stats, .pair-list-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.operation-section h4, .scene-stats h4, .pair-list-section h4 {
  font-size: 14px; color: #374151;
  margin: 0 0 20px 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
}

.form-select:focus {
  outline: none; border-color: #3b82f6;
}

.strategy-section {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
}

.strategy-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-item.disabled { opacity: 0.5; }
.strategy-item input[type="radio"] { cursor: pointer; }
.strategy-item input[type="radio"]:disabled { cursor: not-allowed; }
.strategy-item label { cursor: pointer; font-size: 14px; }

.scene-stats {
  display: flex;
  gap: 24px;
  align-items: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-label { font-size: 12px; color: #64748b; }
.stat-value { font-size: 24px; font-weight: 700; color: #1e40af; }

.pair-list {
  max-height: 400px;
  overflow-y: auto;
}

.pair-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.pair-index {
  font-size: 12px; color: #94a3b8;
  font-weight: 600; min-width: 40px;
}

.pair-devices {
  flex: 1;
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.pair-eval {
  font-size: 12px; color: #64748b;
  background: #f1f5f9;
  padding: 4px 8px;
  border-radius: 4px;
}

.empty-tip {
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 14px;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  max-height: 80vh;
  max-width: 500px;
  width: 90%;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 { font-size: 16px; margin: 0; color: #1e40af; }

.btn-icon {
  width: 28px; height: 28px;
  border: none; background: none;
  font-size: 18px; cursor: pointer; color: #64748b;
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px;
}

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-content { animation: fadeIn 0.3s ease; }

.preview-item {
  font-size: 14px; color: #374151;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  color: #64748b;
  margin: 20px 0 16px 0;
}

.preview-stats {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
}

.preview-stat {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
}

.preview-stat:last-child { border-bottom: none; }

.preview-stat.highlight {
  font-weight: 600;
  color: #1e40af;
}

.preview-label { font-size: 13px; color: #64748b; }
.preview-value { font-size: 14px; color: #374151; font-weight: 500; }

.warning-box {
  background: #fef3c7;
  color: #92400e;
  padding: 12px 16px;
  border-radius: 8px;
  margin-top: 20px;
  font-size: 14px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e2e8f0;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 768px) {
  .scene-stats { flex-direction: column; }
  .operation-section, .pair-list-section { padding: 16px; }
  .pair-item { flex-direction: column; align-items: flex-start; }
}
</style>
