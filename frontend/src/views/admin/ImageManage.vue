<template>
  <div class="image-manage-page">
    <div class="page-header">
      <h1 class="page-title">🖼️ 图像管理</h1>
      <button class="btn-primary" @click="showUploadModal = true">+ 上传图像</button>
    </div>

    <div class="filter-bar">
      <div class="filter-item">
        <label>场景：</label>
        <select v-model="filters.scene_id" @change="fetchImages" class="form-select">
          <option value="">全部</option>
          <option v-for="scene in scenes" :key="scene.id" :value="scene.id">{{ scene.name }}</option>
        </select>
      </div>
      <div class="filter-item">
        <label>机型：</label>
        <select v-model="filters.model_id" @change="fetchImages" class="form-select">
          <option value="">全部</option>
          <option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</option>
        </select>
      </div>
    </div>

    <div class="image-grid">
      <div v-for="img in filteredImages" :key="img.id" class="image-card">
        <div class="image-preview">
          <img v-if="img.thumb_path" :src="img.thumb_path" :alt="img.model_name" />
          <img v-else :src="img.image_path" :alt="img.model_name" />
        </div>
        <div class="image-info">
          <div class="scene-tag">{{ img.scene_name }}</div>
          <div class="model-tag">{{ img.model_name }}</div>
        </div>
      </div>

      <div v-if="filteredImages.length === 0" class="empty-tip">
        暂无图像数据
      </div>
    </div>

    <div class="pagination">
      共 {{ filteredImages.length }} 张图像
    </div>

    <!-- 上传模态框 -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>录入图像及采集表</h2>
          <button class="btn-icon" @click="closeModal">✕</button>
        </div>

        <div class="modal-body">
          <div class="basic-association">
            <h4>基础关联</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>关联场景</label>
                <select v-model="form.scene_id" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="scene in scenes" :key="scene.id" :value="scene.id">{{ scene.name }}</option>
                </select>
              </div>
              <div class="form-group flex1">
                <label>关联机型</label>
                <select v-model="form.model_id" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>图像文件</label>
              <div class="file-drop-zone"
                   :class="{ 'dragover': isDragOver }"
                   @dragover.prevent="isDragOver = true"
                   @dragleave.prevent="isDragOver = false"
                   @drop.prevent="handleDrop"
                   @click="$refs.fileInput.click()">
                <input ref="fileInput" type="file" accept="image/jpeg,image/png" @change="handleFileSelect" style="display:none" />
                <span v-if="!selectedFile">将图像拖拽到此处，或点击上传</span>
                <span v-else class="selected-file">✓ {{ selectedFile.name }}</span>
                <span class="file-hint">(仅支持 jpg/png)</span>
              </div>
            </div>
          </div>

          <div class="quick-action">
            <button class="btn-secondary" @click="showJsonImport = true">📋 从JSON一键导入采集表</button>
          </div>

          <div class="tabs">
            <button class="tab-btn" :class="{ active: activeTab === 0 }" @click="activeTab = 0">① 基础信息</button>
            <button class="tab-btn" :class="{ active: activeTab === 1 }" @click="activeTab = 1">② 场景环境</button>
            <button class="tab-btn" :class="{ active: activeTab === 2 }" @click="activeTab = 2">③ 设备参数</button>
            <button class="tab-btn" :class="{ active: activeTab === 3 }" @click="activeTab = 3">④ ISP参数</button>
          </div>

          <div v-show="activeTab === 0" class="tab-content">
            <h4 class="section-title">── ① 基础信息 (将存入 note_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集时间</label>
                <input v-model="form.note_attrs.capture_time" type="datetime-local" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>采集环境</label>
                <select v-model="form.note_attrs.capture_env" class="form-select">
                  <option value="室外">室外</option>
                  <option value="室内">室内</option>
                  <option value="实验室">实验室</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集人员</label>
                <input v-model="form.note_attrs.capture_person" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>设备编号</label>
                <input v-model="form.note_attrs.device_code" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集地点</label>
                <input v-model="form.note_attrs.capture_location" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>采集目的</label>
                <select v-model="form.note_attrs.capture_purpose" class="form-select">
                  <option value="盲评">盲评</option>
                  <option value="测试">测试</option>
                  <option value="研发">研发</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>特殊说明</label>
              <textarea v-model="form.note_attrs.special_note" class="form-textarea" rows="2"></textarea>
            </div>
          </div>

          <div v-show="activeTab === 1" class="tab-content">
            <h4 class="section-title">── ② 场景环境 (env_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>点位类型</label>
                <input v-model="form.env_attrs.point_type" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>天气</label>
                <input v-model="form.env_attrs.weather" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>季节</label>
                <input v-model="form.env_attrs.season" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>时段</label>
                <input v-model="form.env_attrs.time_period" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>环境色温</label>
                <input v-model="form.env_attrs.env_color_temp" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>环境照度</label>
                <input v-model="form.env_attrs.env_illuminance" class="form-input" />
              </div>
            </div>
            <div class="form-group">
              <label>关系描述</label>
              <textarea v-model="form.env_attrs.relation_desc" class="form-textarea" rows="2"></textarea>
            </div>
          </div>

          <div v-show="activeTab === 2" class="tab-content">
            <h4 class="section-title">── ③ 设备参数 (model_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>设备名</label>
                <input v-model="form.model_attrs.device_name" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>主控型号</label>
                <input v-model="form.model_attrs.main_chip" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>镜头型号</label>
                <input v-model="form.model_attrs.lens_model" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>Sensor型号</label>
                <input v-model="form.model_attrs.sensor_model" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>焦距</label>
                <input v-model="form.model_attrs.focal_length" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>分辨率</label>
                <input v-model="form.model_attrs.resolution" class="form-input" />
              </div>
            </div>
          </div>

          <div v-show="activeTab === 3" class="tab-content">
            <h4 class="section-title">── ④ ISP参数 (isp_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>Sensor Analog Gain</label>
                <input v-model="form.isp_attrs.sensor_analog_gain" type="number" step="0.1" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>Sensor Digital Gain</label>
                <input v-model="form.isp_attrs.sensor_digital_gain" type="number" step="0.1" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>Total Gain</label>
                <input v-model="form.isp_attrs.total_gain" type="number" step="0.1" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>曝光时间</label>
                <input v-model="form.isp_attrs.exposure_time" type="number" step="0.001" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>白平衡 RGain</label>
                <input v-model="form.isp_attrs.wb_r_gain" type="number" step="0.01" class="form-input" />
              </div>
            </div>
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="closeModal">取消</button>
          <button class="btn-primary" @click="submitImage" :disabled="saving">
            {{ saving ? '上传中...' : '确认录入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- JSON 导入对话框 -->
    <div v-if="showJsonImport" class="modal-overlay" @click.self="showJsonImport = false">
      <div class="modal-content narrow">
        <div class="modal-header">
          <h2>导入采集表数据</h2>
          <button class="btn-icon" @click="showJsonImport = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="import-hint">请贴入完整的采集表JSON格式数据：</p>
          <textarea v-model="jsonInput" class="json-textarea" rows="10" placeholder='{
  "基础采集信息": {"采集人员": "李四"},
  "场景信息": {"天气": "晴天"},
  "图像/视频参数": {"主控型号": "Hi3516EV300"},
  "ISP参数": {"Total Gain": "1.0"}
}'></textarea>
          <div class="import-note">ℹ️ 系统将自动按规则拆解并填充至4个Tab页内</div>
          <div v-if="jsonError" class="error-message">{{ jsonError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showJsonImport = false">取消</button>
          <button class="btn-primary" @click="importJsonData">确认导入</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'

const authStore = useAuthStore()

const images = ref([])
const scenes = ref([])
const models = ref([])
const showUploadModal = ref(false)
const showJsonImport = ref(false)
const activeTab = ref(0)
const saving = ref(false)
const errorMessage = ref('')
const jsonInput = ref('')
const jsonError = ref('')
const isDragOver = ref(false)
const selectedFile = ref(null)

const filters = ref({
  scene_id: '',
  model_id: '',
})

const form = ref({
  scene_id: '',
  model_id: '',
  model_attrs: {
    device_name: '', main_chip: '', lens_model: '',
    sensor_model: '', focal_length: '', resolution: '',
  },
  env_attrs: {
    point_type: '', weather: '', season: '',
    time_period: '', env_color_temp: '', env_illuminance: '',
    relation_desc: '',
  },
  isp_attrs: {
    sensor_analog_gain: '', sensor_digital_gain: '',
    total_gain: '', exposure_time: '', wb_r_gain: '',
  },
  note_attrs: {
    capture_time: '', capture_env: '室外',
    capture_person: '', device_code: '',
    capture_location: '', capture_purpose: '盲评', special_note: '',
  },
})

const filteredImages = computed(() => {
  return images.value.filter(img => {
    if (filters.value.scene_id && img.scene_id !== filters.value.scene_id) return false
    if (filters.value.model_id && img.model_id !== filters.value.model_id) return false
    return true
  })
})

async function fetchData() {
  try {
    const [imagesData, scenesData, modelsData] = await Promise.all([
      fetch('/api/admin/images', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
      fetch('/api/admin/scenes', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
      fetch('/api/admin/models', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
    ])
    images.value = imagesData
    scenes.value = scenesData
    models.value = modelsData
  } catch (e) {
    console.error('获取数据失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '获取数据失败', 'error')
  }
}

function fetchImages() {
  fetchData()
}

function handleFileSelect(e) {
  const file = e.target.files[0]
  if (file) selectedFile.value = file
}

function handleDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg']
    if (!validTypes.includes(file.type)) {
      if (window.showAdminToast) window.showAdminToast('仅支持 jpg/png 格式', 'error')
      return
    }
    selectedFile.value = file
  }
}

function importJsonData() {
  jsonError.value = ''
  try {
    const json = JSON.parse(jsonInput.value)

    // 基础采集信息 → note_attrs
    if (json['基础采集信息']) {
      const mapping = {
        '采集时间': 'capture_time',
        '采集人员': 'capture_person',
        '采集地点': 'capture_location',
        '采集环境': 'capture_env',
        '设备编号': 'device_code',
        '采集目的': 'capture_purpose',
        '特殊说明': 'special_note'
      }
      for (const [key, value] of Object.entries(json['基础采集信息'])) {
        const mappedKey = mapping[key] || key
        form.value.note_attrs[mappedKey] = value
      }
    }

    // 场景信息 → env_attrs
    if (json['场景信息']) {
      const mapping = {
        '点位类型': 'point_type',
        '天气': 'weather',
        '季节': 'season',
        '时段': 'time_period',
        '照明模式': 'lighting_mode',
        '光照类型': 'light_type',
        '目标类型': 'target_type',
        '环境色温': 'env_color_temp',
        '样机计算色温': 'calc_color_temp',
        '环境照度': 'env_illuminance',
        '运动状态': 'motion_state',
        '关系描述': 'relation_desc'
      }
      for (const [key, value] of Object.entries(json['场景信息'])) {
        const mappedKey = mapping[key] || key
        form.value.env_attrs[mappedKey] = value
      }
    }

    // 图像视频参数 → model_attrs
    if (json['图像视频参数'] || json['图像/视频参数']) {
      const data = json['图像视频参数'] || json['图像/视频参数']
      const mapping = {
        '设备名': 'device_name',
        '主控型号': 'main_chip',
        '镜头型号': 'lens_model',
        '焦距': 'focal_length',
        '光圈': 'aperture',
        'Sensor型号': 'sensor_model',
        '白光灯珠料号': 'white_led',
        '红外灯珠料号': 'ir_led',
        '分辨率': 'resolution',
        '采集帧率': 'frame_rate',
        '固件版本': 'firmware_version',
        '壳体信息': 'housing_info',
        '场景模式': 'scene_mode'
      }
      for (const [key, value] of Object.entries(data)) {
        const mappedKey = mapping[key] || key
        form.value.model_attrs[mappedKey] = value
      }
    }

    // ISP参数 → isp_attrs
    if (json['ISP参数']) {
      const mapping = {
        'Sensor Analog Gain': 'sensor_analog_gain',
        'Sensor Digital Gain': 'sensor_digital_gain',
        'Total Gain': 'total_gain',
        '曝光时间': 'exposure_time',
        '白平衡 RGain': 'wb_r_gain'
      }
      for (const [key, value] of Object.entries(json['ISP参数'])) {
        const mappedKey = mapping[key] || key
        form.value.isp_attrs[mappedKey] = value
      }
    }

    showJsonImport.value = false
    jsonInput.value = ''
    activeTab.value = 0
    if (window.showAdminToast) window.showAdminToast('JSON 导入成功，数据已填充到对应Tab', 'success')
  } catch (e) {
    jsonError.value = 'JSON 格式错误'
  }
}

function closeModal() {
  showUploadModal.value = false
  showJsonImport.value = false
  activeTab.value = 0
  resetForm()
}

function resetForm() {
  form.value = {
    scene_id: '', model_id: '',
    model_attrs: { device_name: '', main_chip: '', lens_model: '', sensor_model: '', focal_length: '', resolution: '' },
    env_attrs: { point_type: '', weather: '', season: '', time_period: '', env_color_temp: '', env_illuminance: '', relation_desc: '' },
    isp_attrs: { sensor_analog_gain: '', sensor_digital_gain: '', total_gain: '', exposure_time: '', wb_r_gain: '' },
    note_attrs: { capture_time: '', capture_env: '室外', capture_person: '', device_code: '', capture_location: '', capture_purpose: '盲评', special_note: '' },
  }
  selectedFile.value = null
  errorMessage.value = ''
  jsonInput.value = ''
  jsonError.value = ''
}

async function submitImage() {
  if (!form.value.scene_id || !form.value.model_id) {
    errorMessage.value = '请选择关联场景和机型'
    return
  }
  if (!selectedFile.value) {
    errorMessage.value = '请上传图像文件'
    return
  }

  saving.value = true
  errorMessage.value = ''

  try {
    const formData = new FormData()
    formData.append('scene_id', form.value.scene_id)
    formData.append('model_id', form.value.model_id)
    formData.append('model_attrs', JSON.stringify(form.value.model_attrs))
    formData.append('env_attrs', JSON.stringify(form.value.env_attrs))
    formData.append('isp_attrs', JSON.stringify(form.value.isp_attrs))
    formData.append('note_attrs', JSON.stringify(form.value.note_attrs))
    formData.append('image_file', selectedFile.value)

    const res = await fetch('/api/admin/images', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` },
      body: formData,
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '上传失败')
    }

    if (window.showAdminToast) window.showAdminToast('图像上传成功', 'success')
    closeModal()
    await fetchData()
  } catch (e) {
    errorMessage.value = e.message || '上传失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.image-manage-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e40af;
  margin: 0;
}

.btn-primary, .btn-secondary, .btn-cancel {
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}

.btn-primary { background: #3b82f6; color: #fff; border: none; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { background: #eff6ff; color: #3b82f6; border: 1px solid #3b82f6; }
.btn-secondary:hover { background: #dbeafe; }
.btn-cancel { background: #fff; color: #64748b; border: 1px solid #e2e8f0; }

.filter-bar {
  display: flex;
  gap: 16px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-item label {
  font-size: 13px; color: #374151; font-weight: 500; white-space: nowrap; 
}

.form-select, .form-input, .form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
}

.form-select:focus, .form-input:focus, .form-textarea:focus {
  outline: none; border-color: #3b82f6;
}

.form-textarea { resize: vertical; font-family: inherit; }

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.image-card {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: all 0.2s;
}

.image-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.image-preview {
  width: 100%;
  aspect-ratio: 4/3;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-info {
  padding: 12px;
}

.scene-tag, .model-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 6px;
}

.scene-tag { background: #dbeafe; color: #1e40af; }
.model-tag { background: #dcfce7; color: #16a34a; }

.empty-tip {
  grid-column: 1 / -1;
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 14px;
}

.pagination {
  text-align: center;
  color: #64748b;
  font-size: 13px;
  padding: 16px;
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
  max-height: 90vh;
  max-width: 900px;
  width: 90%;
}

.modal-content.narrow {
  max-width: 500px;
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

.basic-association {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.basic-association h4 {
  margin: 0 0 16px 0;
  font-size: 14px; color: #374151;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.flex1 { flex: 1; }

.file-drop-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.file-drop-zone:hover, .file-drop-zone.dragover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.file-hint {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}

.selected-file {
  color: #16a34a;
  font-weight: 500;
}

.quick-action {
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 20px;
}

.tab-btn {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  cursor: pointer;
  color: #64748b;
}

.tab-btn:hover { color: #374151; }
.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

.section-title {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 16px;
}

.import-hint { font-size: 13px; color: #374151; margin-bottom: 8px; }
.import-note { font-size: 12px; color: #64748b; margin-top: 8px; }

.json-textarea {
  width: 100%;
  height: 150px;
  font-family: monospace;
  font-size: 12px;
  padding: 12px;
}

.error-message {
  color: #dc2626;
  font-size: 13px;
  margin-top: 12px;
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
  .filter-bar { flex-direction: column; }
  .form-row { flex-direction: column; }
  .modal-content { width: 95%; }
}
</style>
