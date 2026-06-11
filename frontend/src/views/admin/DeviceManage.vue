<template>
  <div class="device-manage-page">
    <div class="page-header">
      <h1 class="page-title">📱 设备管理</h1>
      <button class="btn-primary" @click="showCreateDrawer = true">+ 新增设备</button>
    </div>

    <div class="device-list">
      <div class="device-table">
      <div class="device-item header">
        <span class="col-name">设备名称</span>
        <span class="col-chip filterable" @click.stop="toggleFilter('main_chip')">
          主控型号
          <span class="filter-icon" :class="{ active: filters.main_chip }">▼</span>
          <div v-if="activeFilter === 'main_chip'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.main_chip" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.main_chip }" @click="setFilter('main_chip', '')">全部</div>
              <div v-for="val in filteredMainChipOptions" :key="val" class="filter-option" :class="{ selected: filters.main_chip === val }" @click="setFilter('main_chip', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-lens">镜头型号</span>
        <span class="col-sensor filterable" @click.stop="toggleFilter('sensor_model')">
          Sensor
          <span class="filter-icon" :class="{ active: filters.sensor_model }">▼</span>
          <div v-if="activeFilter === 'sensor_model'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.sensor_model" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.sensor_model }" @click="setFilter('sensor_model', '')">全部</div>
              <div v-for="val in filteredSensorOptions" :key="val" class="filter-option" :class="{ selected: filters.sensor_model === val }" @click="setFilter('sensor_model', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-aperture filterable" @click.stop="toggleFilter('aperture')">
          光圈
          <span class="filter-icon" :class="{ active: filters.aperture }">▼</span>
          <div v-if="activeFilter === 'aperture'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.aperture" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.aperture }" @click="setFilter('aperture', '')">全部</div>
              <div v-for="val in filteredApertureOptions" :key="val" class="filter-option" :class="{ selected: filters.aperture === val }" @click="setFilter('aperture', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-focal filterable" @click.stop="toggleFilter('focal_length')">
          焦距
          <span class="filter-icon" :class="{ active: filters.focal_length }">▼</span>
          <div v-if="activeFilter === 'focal_length'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.focal_length" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.focal_length }" @click="setFilter('focal_length', '')">全部</div>
              <div v-for="val in filteredFocalOptions" :key="val" class="filter-option" :class="{ selected: filters.focal_length === val }" @click="setFilter('focal_length', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-resolution filterable" @click.stop="toggleFilter('resolution')">
          分辨率
          <span class="filter-icon" :class="{ active: filters.resolution }">▼</span>
          <div v-if="activeFilter === 'resolution'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.resolution" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.resolution }" @click="setFilter('resolution', '')">全部</div>
              <div v-for="val in filteredResolutionOptions" :key="val" class="filter-option" :class="{ selected: filters.resolution === val }" @click="setFilter('resolution', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-frame">帧率</span>
        <span class="col-led">白光灯珠</span>
        <span class="col-led">红外灯珠</span>
        <span class="col-housing">壳体</span>
        <span class="col-attrs">扩展参数</span>
        <span class="col-count">图像数</span>
        <span class="col-action">操作</span>
      </div>

      <div v-for="device in paginatedDevices" :key="device.id" class="device-item">
        <span class="col-name" :title="device.name">{{ device.name }}</span>
        <span class="col-chip" :title="device.main_chip">{{ device.main_chip || '-' }}</span>
        <span class="col-lens" :title="device.lens_model">{{ device.lens_model || '-' }}</span>
        <span class="col-sensor" :title="device.sensor_model">{{ device.sensor_model || '-' }}</span>
        <span class="col-aperture" :title="device.aperture">{{ device.aperture || '-' }}</span>
        <span class="col-focal" :title="device.focal_length">{{ device.focal_length || '-' }}</span>
        <span class="col-resolution" :title="device.resolution">{{ device.resolution || '-' }}</span>
        <span class="col-frame" :title="device.frame_rate">{{ device.frame_rate || '-' }}</span>
        <span class="col-led" :title="device.white_led">{{ device.white_led || '-' }}</span>
        <span class="col-led" :title="device.ir_led">{{ device.ir_led || '-' }}</span>
        <span class="col-housing" :title="device.housing_info">{{ device.housing_info || '-' }}</span>
        <span class="col-attrs" :title="formatAttrs(device.device_attrs)">{{ formatAttrs(device.device_attrs) }}</span>
        <span class="col-count">{{ device.image_count }}</span>
        <span class="col-action">
          <button class="btn-sm btn-edit" @click="editDevice(device)">编辑</button>
        </span>
      </div>

      <div v-if="filteredDevices.length === 0" class="empty-tip">
        暂无设备数据
      </div>
      </div>

      <!-- 分页 -->
      <div v-if="filteredDevices.length > 0" class="pagination">
        <div class="page-size">
          <label>每页</label>
          <select v-model.number="pageSize" @change="currentPage = 1">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <label>条</label>
        </div>
        <span class="page-info">共 {{ filteredDevices.length }} 条，{{ currentPage }}/{{ totalPages }} 页</span>
        <div class="page-btns">
          <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
          <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
        </div>
      </div>
    </div>

    <!-- 新增/编辑抽屉 -->
    <div v-if="showCreateDrawer || showEditDrawer" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer-content wide">
        <div class="drawer-header">
          <h2>{{ showEditDrawer ? '编辑设备' : '新增设备' }}</h2>
          <button class="btn-icon" @click="closeDrawer">✕</button>
        </div>

        <div class="drawer-body">
          <div class="quick-action">
            <button class="btn-secondary" @click="showImportJson = true">📋 导入JSON配置</button>
          </div>

          <div v-if="showImportJson" class="import-json-box">
            <textarea v-model="jsonInput" class="json-textarea" placeholder='请粘贴完整的设备配置 JSON，如：
{
  "设备名": "632-A4 12.0",
  "主控型号": "Hi3519AV100",
  "镜头型号": "LS-1235",
  "Sensor型号": "IMX335",
  "光圈": "f/1.6",
  "焦距": "12.0mm",
  "分辨率": "2592×1944",
  "帧率": "30fps",
  "白光灯珠料号": "LED-W-08",
  "红外灯珠料号": "LED-R-08",
  "壳体信息": "SH-632-B",
  "固件版本": "v4.0"
}'></textarea>
            <div class="import-actions">
              <button class="btn-cancel" @click="showImportJson = false">取消</button>
              <button class="btn-primary" @click="importJson">确认导入</button>
            </div>
          </div>

          <div class="warning-tip">⚠️ 命名规范：同一设备不同固件需有后缀（如 632-WB4_v2.0）</div>

          <div class="form-group">
            <label>设备名称</label>
            <input v-model="form.name" class="form-input" />
          </div>

          <h4 class="section-title">── 核心参数 (高频筛选) ───</h4>
          <div class="form-row">
            <div class="form-group flex1">
              <label>主控型号</label>
              <input v-model="form.main_chip" class="form-input" />
            </div>
            <div class="form-group flex1">
              <label>镜头型号</label>
              <input v-model="form.lens_model" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group flex1">
              <label>Sensor型号</label>
              <input v-model="form.sensor_model" class="form-input" />
            </div>
            <div class="form-group flex1">
              <label>光圈</label>
              <input v-model="form.aperture" class="form-input" placeholder="如 f/1.6" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group flex1">
              <label>焦距</label>
              <input v-model="form.focal_length" class="form-input" placeholder="如 2.8mm" />
            </div>
            <div class="form-group flex1">
              <label>分辨率</label>
              <input v-model="form.resolution" class="form-input" placeholder="如 1920×1080" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group flex1">
              <label>帧率</label>
              <input v-model="form.frame_rate" class="form-input" placeholder="如 30fps" />
            </div>
            <div class="form-group flex1">
              <label>壳体信息</label>
              <input v-model="form.housing_info" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group flex1">
              <label>白光灯珠料号</label>
              <input v-model="form.white_led" class="form-input" placeholder="如 LED-W-08" />
            </div>
            <div class="form-group flex1">
              <label>红外灯珠料号</label>
              <input v-model="form.ir_led" class="form-input" placeholder="如 LED-R-08" />
            </div>
          </div>

          <h4 class="section-title">── 扩展参数 ───</h4>
          <div class="form-row">
            <div class="form-group flex1">
              <label>固件版本</label>
              <input v-model="form.device_attrs.firmware_version" class="form-input" />
            </div>
          </div>

          <div class="custom-params">
            <div v-for="(param, idx) in customParams" :key="idx" class="form-row">
              <div class="form-group flex2">
                <label>参数名</label>
                <input v-model="param.key" class="form-input" />
              </div>
              <div class="form-group flex2">
                <label>参数值</label>
                <input v-model="param.value" class="form-input" />
              </div>
              <button class="btn-icon btn-remove" @click="removeCustomParam(idx)">✕</button>
            </div>
          </div>
          <button class="btn-sm btn-add" @click="addCustomParam">+ 添加自定义参数</button>

          <div class="form-group">
            <label>设备特点</label>
            <textarea v-model="form.features" class="form-textarea" rows="3"></textarea>
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>

        <div class="drawer-footer">
          <button class="btn-cancel" @click="closeDrawer">取消</button>
          <button class="btn-primary" @click="submitDevice" :disabled="saving">
            {{ saving ? '保存中...' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'

const authStore = useAuthStore()

const devices = ref([])
const showCreateDrawer = ref(false)
const showEditDrawer = ref(false)
const showImportJson = ref(false)
const editingId = ref(null)
const saving = ref(false)
const errorMessage = ref('')
const jsonInput = ref('')

// 筛选和分页
const activeFilter = ref(null)
const filters = ref({
  main_chip: '',
  sensor_model: '',
  focal_length: '',
  aperture: '',
  resolution: '',
})
const filterSearch = ref({
  main_chip: '',
  sensor_model: '',
  focal_length: '',
  aperture: '',
  resolution: '',
})
const currentPage = ref(1)
const pageSize = ref(10)

const customParams = ref([])

const form = ref({
  name: '',
  main_chip: '',
  lens_model: '',
  sensor_model: '',
  aperture: '',
  focal_length: '',
  resolution: '',
  frame_rate: '',
  white_led: '',
  ir_led: '',
  housing_info: '',
  device_attrs: {
    firmware_version: '',
    scene_mode: '',
  },
  features: '',
})

// 筛选逻辑
function toggleFilter(column) {
  activeFilter.value = activeFilter.value === column ? null : column
}

function setFilter(column, value) {
  filters.value[column] = value
  currentPage.value = 1
  activeFilter.value = null
}

function closeAllFilters() {
  activeFilter.value = null
}

// 格式化扩展参数
function formatAttrs(attrs) {
  if (!attrs || typeof attrs !== 'object') return '-'
  const entries = Object.entries(attrs).filter(([k, v]) => v)
  if (entries.length === 0) return '-'
  return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
}

// 唯一值列表
const uniqueMainChips = computed(() => [...new Set(devices.value.map(d => d.main_chip).filter(Boolean))].sort())
const uniqueSensors = computed(() => [...new Set(devices.value.map(d => d.sensor_model).filter(Boolean))].sort())
const uniqueApertures = computed(() => [...new Set(devices.value.map(d => d.aperture).filter(Boolean))].sort())
const uniqueFocals = computed(() => [...new Set(devices.value.map(d => d.focal_length).filter(Boolean))].sort())
const uniqueResolutions = computed(() => [...new Set(devices.value.map(d => d.resolution).filter(Boolean))].sort())

// 搜索过滤后的选项
const filteredMainChipOptions = computed(() => {
  const search = filterSearch.value.main_chip.toLowerCase()
  return search ? uniqueMainChips.value.filter(v => v.toLowerCase().includes(search)) : uniqueMainChips.value
})
const filteredSensorOptions = computed(() => {
  const search = filterSearch.value.sensor_model.toLowerCase()
  return search ? uniqueSensors.value.filter(v => v.toLowerCase().includes(search)) : uniqueSensors.value
})
const filteredApertureOptions = computed(() => {
  const search = filterSearch.value.aperture.toLowerCase()
  return search ? uniqueApertures.value.filter(v => v.toLowerCase().includes(search)) : uniqueApertures.value
})
const filteredFocalOptions = computed(() => {
  const search = filterSearch.value.focal_length.toLowerCase()
  return search ? uniqueFocals.value.filter(v => v.toLowerCase().includes(search)) : uniqueFocals.value
})
const filteredResolutionOptions = computed(() => {
  const search = filterSearch.value.resolution.toLowerCase()
  return search ? uniqueResolutions.value.filter(v => v.toLowerCase().includes(search)) : uniqueResolutions.value
})

// 筛选后的数据
const filteredDevices = computed(() => {
  return devices.value.filter(d => {
    if (filters.value.main_chip && d.main_chip !== filters.value.main_chip) return false
    if (filters.value.sensor_model && d.sensor_model !== filters.value.sensor_model) return false
    if (filters.value.aperture && d.aperture !== filters.value.aperture) return false
    if (filters.value.focal_length && d.focal_length !== filters.value.focal_length) return false
    if (filters.value.resolution && d.resolution !== filters.value.resolution) return false
    return true
  })
})

// 分页
const totalPages = computed(() => Math.max(1, Math.ceil(filteredDevices.value.length / pageSize.value)))
const paginatedDevices = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredDevices.value.slice(start, start + pageSize.value)
})

async function fetchDevices() {
  try {
    const data = await fetch('/api/admin/devices', {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    }).then(r => r.json())
    devices.value = data
  } catch (e) {
    console.error('获取设备失败:', e)
    if (window.showAdminToast) window.showAdminToast(e.message || '获取设备失败', 'error')
  }
}

function editDevice(device) {
  editingId.value = device.id
  form.value = {
    name: device.name,
    main_chip: device.main_chip || '',
    lens_model: device.lens_model || '',
    sensor_model: device.sensor_model || '',
    aperture: device.aperture || '',
    focal_length: device.focal_length || '',
    resolution: device.resolution || '',
    frame_rate: device.frame_rate || '',
    white_led: device.white_led || '',
    ir_led: device.ir_led || '',
    housing_info: device.housing_info || '',
    device_attrs: { ...(device.device_attrs || {}) },
    features: device.features || '',
  }

  // 提取已知字段外自定义参数
  customParams.value = []
  const knownFields = ['firmware_version', 'scene_mode']
  for (const [key, value] of Object.entries(device.device_attrs || {})) {
    if (!knownFields.includes(key)) {
      customParams.value.push({ key, value })
    }
  }

  showEditDrawer.value = true
  errorMessage.value = ''
}

function importJson() {
  try {
    const json = JSON.parse(jsonInput.value)

    // 中文字段名到表单字段的映射
    const fieldMapping = {
      '设备名': 'name',
      '主控型号': 'main_chip',
      '镜头型号': 'lens_model',
      'Sensor型号': 'sensor_model',
      '光圈': 'aperture',
      '焦距': 'focal_length',
      '分辨率': 'resolution',
      '帧率': 'frame_rate',
      '白光灯珠料号': 'white_led',
      '红外灯珠料号': 'ir_led',
      '壳体信息': 'housing_info',
      // 扩展参数
      '固件版本': 'firmware_version',
    }

    for (const [key, value] of Object.entries(json)) {
      const mappedField = fieldMapping[key] || key

      if (mappedField === 'name') {
        form.value.name = String(value)
      } else if (mappedField === 'firmware_version') {
        form.value.device_attrs.firmware_version = String(value)
      } else if (mappedField === 'scene_mode') {
        form.value.device_attrs.scene_mode = String(value)
      } else if (mappedField in form.value) {
        form.value[mappedField] = String(value)
      } else {
        // 无法匹配的字段作为自定义参数
        const existingIdx = customParams.value.findIndex(p => p.key === key)
        if (existingIdx >= 0) {
          customParams.value[existingIdx].value = String(value)
        } else {
          customParams.value.push({ key, value: String(value) })
        }
      }
    }
    showImportJson.value = false
    jsonInput.value = ''
    if (window.showAdminToast) window.showAdminToast('JSON 导入成功', 'success')
  } catch (e) {
    if (window.showAdminToast) window.showAdminToast('JSON 格式错误', 'error')
  }
}

function addCustomParam() {
  customParams.value.push({ key: '', value: '' })
}

function removeCustomParam(idx) {
  customParams.value.splice(idx, 1)
}

function closeDrawer() {
  showCreateDrawer.value = false
  showEditDrawer.value = false
  showImportJson.value = false
  editingId.value = null
  form.value = {
    name: '', main_chip: '', lens_model: '', sensor_model: '',
    aperture: '', focal_length: '', resolution: '',
    frame_rate: '', white_led: '', ir_led: '', housing_info: '',
    device_attrs: { firmware_version: '', scene_mode: '' },
    features: '',
  }
  customParams.value = []
  errorMessage.value = ''
  jsonInput.value = ''
}

async function submitDevice() {
  if (!form.value.name) {
    errorMessage.value = '请填写设备名称'
    return
  }

  saving.value = true
  errorMessage.value = ''

  try {
    // 构建完整的 device_attrs
    const fullDeviceAttrs = {
      firmware_version: form.value.device_attrs.firmware_version || '',
      scene_mode: form.value.device_attrs.scene_mode || '',
    }
    for (const param of customParams.value) {
      if (param.key) {
        fullDeviceAttrs[param.key] = param.value
      }
    }

    const url = editingId.value ? `/api/admin/devices/${editingId.value}` : '/api/admin/devices'
    const method = editingId.value ? 'PUT' : 'POST'

    const body = {
      name: form.value.name,
      main_chip: form.value.main_chip,
      lens_model: form.value.lens_model,
      sensor_model: form.value.sensor_model,
      aperture: form.value.aperture,
      focal_length: form.value.focal_length,
      resolution: form.value.resolution,
      frame_rate: form.value.frame_rate,
      white_led: form.value.white_led,
      ir_led: form.value.ir_led,
      housing_info: form.value.housing_info,
      device_attrs: fullDeviceAttrs,
      features: form.value.features,
    }

    const res = await fetch(url, {
      method,
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }

    if (window.showAdminToast) {
      window.showAdminToast(editingId.value ? '修改成功' : '创建成功', 'success')
    }
    closeDrawer()
    await fetchDevices()
  } catch (e) {
    errorMessage.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchDevices()
  document.addEventListener('click', closeAllFilters)
})
</script>

<style scoped>
.device-manage-page {
  max-width: 1200px;
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

.btn-primary, .btn-secondary, .btn-cancel, .btn-add, .btn-remove {
  padding: 10px 20px; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}

.btn-primary { background: #3b82f6; color: #fff; border: none; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-secondary { background: #eff6ff; color: #3b82f6; border: 1px solid #3b82f6; }
.btn-secondary:hover { background: #dbeafe; }

.btn-cancel { background: #fff; color: #64748b; border: 1px solid #e2e8f0; }

.btn-add {
  padding: 6px 12px; background: #f0fdf4; color: #16a34a;
  border: 1px dashed #86efac; font-size: 12px;
}
.btn-add:hover { background: #dcfce7; border-style: solid; }

.btn-remove {
  width: 28px; height: 28px; font-size: 14px;
  background: #fef2f2; color: #dc2626; border: none;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
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

.device-list {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow-x: auto;
}

.device-table {
  min-width: 1400px;
  width: 100%;
}

.device-item {
  display: grid;
  grid-template-columns: 150px 100px 90px 90px 70px 70px 90px 90px 60px 80px 80px 70px 150px 60px 70px;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  align-items: center;
  font-size: 13px;
}

.device-item.header {
  background: #f8fafc;
  font-weight: 600;
  color: #64748b;
  position: sticky;
  top: 0;
  z-index: 10;
}

.col-name {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
  position: sticky;
  left: 0;
  background: white;
  z-index: 5;
  padding-right: 8px;
}
.device-item.header .col-name {
  background: #f8fafc;
  z-index: 15;
}

.col-action {
  position: sticky;
  right: 0;
  background: white;
  z-index: 5;
  padding-left: 8px;
}
.device-item.header .col-action {
  background: #f8fafc;
  z-index: 15;
}

.col-chip, .col-lens, .col-sensor, .col-aperture, .col-focal, .col-resolution, .col-frame, .col-led, .col-housing, .col-count {
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-attrs {
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
  max-width: 150px;
}

.btn-sm {
  padding: 6px 12px; border-radius: 6px; font-size: 12px;
  border: 1px solid #e2e8f0; background: #fff; cursor: pointer;
}
.btn-edit:hover { background: #eff6ff; border-color: #3b82f6; color: #3b82f6; }

.empty-tip {
  grid-column: 1 / -1;
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 14px;
}

/* 抽屉样式 */
.drawer-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 100;
}

.drawer-content {
  width: 500px;
  background: white;
  box-shadow: -4px 0 20px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.drawer-content.wide {
  width: 650px;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.drawer-header h2 { font-size: 16px; margin: 0; color: #1e40af; }

.drawer-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.quick-action {
  margin-bottom: 16px;
}

.warning-tip {
  background: #fef3c7;
  color: #92400e;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  color: #64748b;
  margin: 20px 0 16px 0;
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
  gap: 12px;
}

.flex1 { flex: 1; }
.flex2 { flex: 2; }

.custom-params {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
}

.import-json-box {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.json-textarea {
  width: 100%;
  height: 200px;
  font-family: monospace;
  font-size: 12px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 12px;
}

.error-message {
  color: #dc2626;
  font-size: 13px;
  margin-top: 12px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e2e8f0;
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
.filter-icon.active { color: #3b82f6; }
.filter-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 180px;
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
.filter-option:hover { background: #f1f5f9; }
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
  padding: 16px;
  border-top: 1px solid #f1f5f9;
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
  .drawer-content, .drawer-content.wide { width: 100%; }
  .device-item {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px;
  }
  .device-item > span { grid-column: auto; }
  .device-item.header { display: none; }
  .filter-bar { flex-direction: column; }
  .form-row { flex-direction: column; }
}
</style>
