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
        <label>设备：</label>
        <select v-model="filters.device_id" @change="fetchImages" class="form-select">
          <option value="">全部</option>
          <option v-for="device in devices" :key="device.id" :value="device.id">{{ device.name }}</option>
        </select>
      </div>
    </div>

    <div class="image-grid">
      <div v-for="img in filteredImages" :key="img.id" class="image-card">
        <div class="image-preview">
          <img v-if="img.thumb_path" :src="img.thumb_path" :alt="img.device_name" />
          <img v-else :src="img.image_path" :alt="img.device_name" />
          <button class="card-edit-btn" @click.stop="openEditModal(img)" title="编辑">✎</button>
        </div>
        <div class="image-info">
          <div class="scene-tag">{{ img.scene_name }}</div>
          <div class="device-tag">{{ img.device_name }}</div>
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
                <label>关联设备</label>
                <select v-model="form.device_id" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="device in devices" :key="device.id" :value="device.id">{{ device.name }}</option>
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
            <h4 class="section-title">── ③ 设备参数 (shot_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>设备名</label>
                <input v-model="form.shot_attrs.device_name" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>主控型号</label>
                <input v-model="form.shot_attrs.main_chip" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>镜头型号</label>
                <input v-model="form.shot_attrs.lens_model" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>Sensor型号</label>
                <input v-model="form.shot_attrs.sensor_model" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>焦距</label>
                <input v-model="form.shot_attrs.focal_length" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>分辨率</label>
                <input v-model="form.shot_attrs.resolution" class="form-input" />
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

    <!-- 编辑模态框 -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>编辑图像</h2>
          <button class="btn-icon" @click="closeEditModal">✕</button>
        </div>

        <div class="modal-body">
          <div class="edit-image-info">
            <div class="edit-preview">
              <img v-if="editingImage.thumb_path" :src="editingImage.thumb_path" :alt="editingImage.device_name" />
              <img v-else :src="editingImage.image_path" :alt="editingImage.device_name" />
            </div>
            <div class="edit-meta">
              <div><strong>场景：</strong>{{ editingImage.scene_name }}</div>
              <div><strong>设备：</strong>{{ editingImage.device_name }}</div>
              <div><strong>文件：</strong>{{ editingImage.image_path ? editingImage.image_path.split('/').pop() : '-' }}</div>
              <div class="replace-section">
                <label>更换图像（文件名需与原文件一致）：</label>
                <input ref="editFileInput" type="file" accept="image/jpeg,image/png" @change="handleEditFileSelect" style="display:none" />
                <button class="btn-secondary btn-sm" @click="$refs.editFileInput.click()">选择新文件</button>
                <span v-if="editSelectedFile" class="selected-file">✓ {{ editSelectedFile.name }}</span>
                <div v-if="fileError" class="file-error">{{ fileError }}</div>
              </div>
            </div>
          </div>

          <div class="tabs">
            <button class="tab-btn" :class="{ active: editTab === 0 }" @click="editTab = 0">① 基础信息</button>
            <button class="tab-btn" :class="{ active: editTab === 1 }" @click="editTab = 1">② 场景环境</button>
            <button class="tab-btn" :class="{ active: editTab === 2 }" @click="editTab = 2">③ 设备参数</button>
            <button class="tab-btn" :class="{ active: editTab === 3 }" @click="editTab = 3">④ ISP参数</button>
          </div>

          <div v-show="editTab === 0" class="tab-content">
            <h4 class="section-title">── ① 基础信息 (note_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集时间</label>
                <input v-model="editForm.note_attrs.capture_time" type="datetime-local" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>采集环境</label>
                <select v-model="editForm.note_attrs.capture_env" class="form-select">
                  <option value="室外">室外</option>
                  <option value="室内">室内</option>
                  <option value="实验室">实验室</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集人员</label>
                <input v-model="editForm.note_attrs.capture_person" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>设备编号</label>
                <input v-model="editForm.note_attrs.device_code" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>采集地点</label>
                <input v-model="editForm.note_attrs.capture_location" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>采集目的</label>
                <select v-model="editForm.note_attrs.capture_purpose" class="form-select">
                  <option value="盲评">盲评</option>
                  <option value="测试">测试</option>
                  <option value="研发">研发</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>特殊说明</label>
              <textarea v-model="editForm.note_attrs.special_note" class="form-textarea" rows="2"></textarea>
            </div>
          </div>

          <div v-show="editTab === 1" class="tab-content">
            <h4 class="section-title">── ② 场景环境 (env_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>点位类型</label>
                <input v-model="editForm.env_attrs.point_type" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>天气</label>
                <input v-model="editForm.env_attrs.weather" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>季节</label>
                <input v-model="editForm.env_attrs.season" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>时段</label>
                <input v-model="editForm.env_attrs.time_period" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>环境色温</label>
                <input v-model="editForm.env_attrs.env_color_temp" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>环境照度</label>
                <input v-model="editForm.env_attrs.env_illuminance" class="form-input" />
              </div>
            </div>
            <div class="form-group">
              <label>关系描述</label>
              <textarea v-model="editForm.env_attrs.relation_desc" class="form-textarea" rows="2"></textarea>
            </div>
          </div>

          <div v-show="editTab === 2" class="tab-content">
            <h4 class="section-title">── ③ 设备参数 (shot_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>设备名</label>
                <input v-model="editForm.shot_attrs.device_name" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>主控型号</label>
                <input v-model="editForm.shot_attrs.main_chip" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>镜头型号</label>
                <input v-model="editForm.shot_attrs.lens_model" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>Sensor型号</label>
                <input v-model="editForm.shot_attrs.sensor_model" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>焦距</label>
                <input v-model="editForm.shot_attrs.focal_length" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>分辨率</label>
                <input v-model="editForm.shot_attrs.resolution" class="form-input" />
              </div>
            </div>
          </div>

          <div v-show="editTab === 3" class="tab-content">
            <h4 class="section-title">── ④ ISP参数 (isp_attrs) ───</h4>
            <div class="form-row">
              <div class="form-group flex1">
                <label>Sensor Analog Gain</label>
                <input v-model="editForm.isp_attrs.sensor_analog_gain" type="number" step="0.1" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>Sensor Digital Gain</label>
                <input v-model="editForm.isp_attrs.sensor_digital_gain" type="number" step="0.1" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>Total Gain</label>
                <input v-model="editForm.isp_attrs.total_gain" type="number" step="0.1" class="form-input" />
              </div>
              <div class="form-group flex1">
                <label>曝光时间</label>
                <input v-model="editForm.isp_attrs.exposure_time" type="number" step="0.001" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex1">
                <label>白平衡 RGain</label>
                <input v-model="editForm.isp_attrs.wb_r_gain" type="number" step="0.01" class="form-input" />
              </div>
            </div>
          </div>

          <div v-if="editError" class="error-message">{{ editError }}</div>
        </div>

        <div class="modal-footer">
          <button class="btn-danger" @click="confirmDeleteImage">🗑 删除图像</button>
          <div class="footer-right">
            <button class="btn-cancel" @click="closeEditModal">取消</button>
            <button class="btn-primary" @click="submitEdit" :disabled="editSaving">
              {{ editSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal-content narrow">
        <div class="modal-header">
          <h2>确认删除</h2>
          <button class="btn-icon" @click="showDeleteConfirm = false">✕</button>
        </div>
        <div class="modal-body">
          <p>确定要删除这张图像吗？此操作不可恢复。</p>
          <p class="delete-warning">图像文件和缩略图将一并被删除。</p>
          <div v-if="deleteError" class="error-message">{{ deleteError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showDeleteConfirm = false">取消</button>
          <button class="btn-danger" @click="deleteImage" :disabled="deleting">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { apiUpdateImage, apiReplaceImage, apiDeleteImage } from '@/api'

const authStore = useAuthStore()

// ==================== 元信息字段统一配置 ====================
// cnKey: 中文 key（JSON 导入 / 数据库存储）
// enKey: 英文 key（表单 v-model 绑定）
// default: 默认值
const METADATA_FIELDS = {
  note_attrs: [
    { cnKey: '采集时间', enKey: 'capture_time', default: '' },
    { cnKey: '采集环境', enKey: 'capture_env', default: '室外' },
    { cnKey: '采集人员', enKey: 'capture_person', default: '' },
    { cnKey: '设备编号', enKey: 'device_code', default: '' },
    { cnKey: '采集地点', enKey: 'capture_location', default: '' },
    { cnKey: '采集目的', enKey: 'capture_purpose', default: '盲评' },
    { cnKey: '特殊说明', enKey: 'special_note', default: '' },
  ],
  env_attrs: [
    { cnKey: '点位类型', enKey: 'point_type', default: '' },
    { cnKey: '天气', enKey: 'weather', default: '' },
    { cnKey: '季节', enKey: 'season', default: '' },
    { cnKey: '时段', enKey: 'time_period', default: '' },
    { cnKey: '照明模式', enKey: 'lighting_mode', default: '' },
    { cnKey: '光照类型', enKey: 'light_type', default: '' },
    { cnKey: '目标类型', enKey: 'target_type', default: '' },
    { cnKey: '环境色温', enKey: 'env_color_temp', default: '' },
    { cnKey: '样机计算色温', enKey: 'calc_color_temp', default: '' },
    { cnKey: '环境照度', enKey: 'env_illuminance', default: '' },
    { cnKey: '运动状态', enKey: 'motion_state', default: '' },
    { cnKey: '关系描述', enKey: 'relation_desc', default: '' },
  ],
  shot_attrs: [
    { cnKey: '设备名', enKey: 'device_name', default: '' },
    { cnKey: '主控型号', enKey: 'main_chip', default: '' },
    { cnKey: '镜头型号', enKey: 'lens_model', default: '' },
    { cnKey: 'Sensor型号', enKey: 'sensor_model', default: '' },
    { cnKey: '焦距', enKey: 'focal_length', default: '' },
    { cnKey: '光圈', enKey: 'aperture', default: '' },
    { cnKey: '分辨率', enKey: 'resolution', default: '' },
    { cnKey: '白光灯珠料号', enKey: 'white_led', default: '' },
    { cnKey: '红外灯珠料号', enKey: 'ir_led', default: '' },
    { cnKey: '采集帧率', enKey: 'frame_rate', default: '' },
    { cnKey: '固件版本', enKey: 'firmware_version', default: '' },
    { cnKey: '壳体信息', enKey: 'housing_info', default: '' },
    { cnKey: '场景模式', enKey: 'scene_mode', default: '' },
  ],
  isp_attrs: [
    { cnKey: 'Sensor Analog Gain', enKey: 'sensor_analog_gain', default: '' },
    { cnKey: 'Sensor Digital Gain', enKey: 'sensor_digital_gain', default: '' },
    { cnKey: 'Total Gain', enKey: 'total_gain', default: '' },
    { cnKey: '曝光时间', enKey: 'exposure_time', default: '' },
    { cnKey: '白平衡 RGain', enKey: 'wb_r_gain', default: '' },
  ],
}

// JSON 中文组名 → attrs group 名
const JSON_GROUP_MAP = {
  '基础采集信息': 'note_attrs',
  '场景信息': 'env_attrs',
  '图像视频参数': 'shot_attrs',
  '图像/视频参数': 'shot_attrs',
  'ISP参数': 'isp_attrs',
}

// 从 METADATA_FIELDS 生成默认值
function getDefaults() {
  const result = {}
  for (const [group, fields] of Object.entries(METADATA_FIELDS)) {
    result[group] = {}
    for (const f of fields) {
      result[group][f.enKey] = f.default
    }
  }
  return result
}

// 从 METADATA_FIELDS 生成中文→英文映射
function getCnToEnMap(group) {
  const map = {}
  for (const f of METADATA_FIELDS[group]) {
    map[f.cnKey] = f.enKey
  }
  return map
}

// 数据库 key 归一化：中文 key → 英文 key
function normalizeAttrs(attrs, group) {
  if (!attrs) return {}
  const map = getCnToEnMap(group)
  const result = {}
  for (const [k, v] of Object.entries(attrs)) {
    result[map[k] || k] = v
  }
  return result
}

// 采集时间格式转换：数据库 "2026/05/12/21/30/00" ↔ datetime-local "2026-05-12T21:30"
function toDatetimeLocal(val) {
  if (!val || typeof val !== 'string') return ''
  // "2026/05/12/21/30/00" → "2026-05-12T21:30"
  const m = val.match(/^(\d{4})\/(\d{2})\/(\d{2})\/(\d{2})\/(\d{2})/)
  return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}` : val
}

function fromDatetimeLocal(val) {
  if (!val) return ''
  // "2026-05-12T21:30" → "2026/05/12/21/30/00"
  const m = val.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/)
  return m ? `${m[1]}/${m[2]}/${m[3]}/${m[4]}/${m[5]}/00` : val
}

const images = ref([])
const scenes = ref([])
const devices = ref([])
const showUploadModal = ref(false)
const showJsonImport = ref(false)
const activeTab = ref(0)
const saving = ref(false)
const errorMessage = ref('')
const jsonInput = ref('')
const jsonError = ref('')
const isDragOver = ref(false)
const selectedFile = ref(null)

// 编辑状态
const showEditModal = ref(false)
const editingImage = ref({})
const editTab = ref(0)
const editSaving = ref(false)
const editError = ref('')
const fileError = ref('')
const editSelectedFile = ref(null)
const editForm = ref({
  shot_attrs: {}, env_attrs: {}, isp_attrs: {}, note_attrs: {},
})

// 删除状态
const showDeleteConfirm = ref(false)
const deleteError = ref('')
const deleting = ref(false)

const filters = ref({
  scene_id: '',
  device_id: '',
})

const form = ref({
  scene_id: '',
  device_id: '',
  ...getDefaults(),
})

const filteredImages = computed(() => {
  return images.value.filter(img => {
    if (filters.value.scene_id && img.scene_id !== filters.value.scene_id) return false
    if (filters.value.device_id && img.device_id !== filters.value.device_id) return false
    return true
  })
})

async function fetchData() {
  try {
    const [imagesData, scenesData, devicesData] = await Promise.all([
      fetch('/api/admin/images', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
      fetch('/api/admin/scenes', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
      fetch('/api/admin/devices', { headers: { 'Authorization': `Bearer ${authStore.token}` } }).then(r => r.json()),
    ])
    images.value = imagesData
    scenes.value = scenesData
    devices.value = devicesData
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

    for (const [cnGroupName, jsonGroupName] of Object.entries(JSON_GROUP_MAP)) {
      const groupData = json[cnGroupName]
      if (!groupData) continue
      const cnToEn = getCnToEnMap(jsonGroupName)
      for (const [key, value] of Object.entries(groupData)) {
        const enKey = cnToEn[key] || key
        form.value[jsonGroupName][enKey] = value
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
  form.value = { scene_id: '', device_id: '', ...getDefaults() }
  selectedFile.value = null
  errorMessage.value = ''
  jsonInput.value = ''
  jsonError.value = ''
}

async function submitImage() {
  if (!form.value.scene_id || !form.value.device_id) {
    errorMessage.value = '请选择关联场景和设备'
    return
  }
  if (!selectedFile.value) {
    errorMessage.value = '请上传图像文件'
    return
  }

  saving.value = true
  errorMessage.value = ''

  try {
    const noteAttrs = { ...form.value.note_attrs }
    noteAttrs.capture_time = fromDatetimeLocal(noteAttrs.capture_time)

    const formData = new FormData()
    formData.append('scene_id', form.value.scene_id)
    formData.append('device_id', form.value.device_id)
    formData.append('shot_attrs', JSON.stringify(form.value.shot_attrs))
    formData.append('env_attrs', JSON.stringify(form.value.env_attrs))
    formData.append('isp_attrs', JSON.stringify(form.value.isp_attrs))
    formData.append('note_attrs', JSON.stringify(noteAttrs))
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

function openEditModal(img) {
  editingImage.value = { ...img }
  const defaults = getDefaults()
  editForm.value = {
    shot_attrs: { ...defaults.shot_attrs, ...normalizeAttrs(img.shot_attrs, 'shot_attrs') },
    env_attrs: { ...defaults.env_attrs, ...normalizeAttrs(img.env_attrs, 'env_attrs') },
    isp_attrs: { ...defaults.isp_attrs, ...normalizeAttrs(img.isp_attrs, 'isp_attrs') },
    note_attrs: { ...defaults.note_attrs, ...normalizeAttrs(img.note_attrs, 'note_attrs') },
  }
  // 采集时间格式转换
  editForm.value.note_attrs.capture_time = toDatetimeLocal(editForm.value.note_attrs.capture_time)
  editSelectedFile.value = null
  editError.value = ''
  fileError.value = ''
  editTab.value = 0
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  editingImage.value = {}
  editSelectedFile.value = null
  editError.value = ''
  fileError.value = ''
}

function handleEditFileSelect(e) {
  const file = e.target.files[0]
  if (file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg']
    if (!validTypes.includes(file.type)) {
      fileError.value = '仅支持 jpg/png 格式'
      return
    }
    // 校验文件名必须与原文件一致
    const oldFilename = editingImage.value.image_path.split('/').pop()
    if (file.name !== oldFilename) {
      fileError.value = `文件名不匹配：原文件为 "${oldFilename}"，请上传同名文件`
      editSelectedFile.value = null
      return
    }
    editSelectedFile.value = file
    fileError.value = ''
  }
}

async function submitEdit() {
  editSaving.value = true
  editError.value = ''

  try {
    // 采集时间格式转换
    const noteAttrs = { ...editForm.value.note_attrs }
    noteAttrs.capture_time = fromDatetimeLocal(noteAttrs.capture_time)

    if (editSelectedFile.value) {
      // 替换文件
      const formData = new FormData()
      formData.append('image_file', editSelectedFile.value)
      formData.append('shot_attrs', JSON.stringify(editForm.value.shot_attrs))
      formData.append('env_attrs', JSON.stringify(editForm.value.env_attrs))
      formData.append('isp_attrs', JSON.stringify(editForm.value.isp_attrs))
      formData.append('note_attrs', JSON.stringify(noteAttrs))
      await apiReplaceImage(editingImage.value.id, formData)
    } else {
      // 仅更新元信息
      const formData = new FormData()
      formData.append('shot_attrs', JSON.stringify(editForm.value.shot_attrs))
      formData.append('env_attrs', JSON.stringify(editForm.value.env_attrs))
      formData.append('isp_attrs', JSON.stringify(editForm.value.isp_attrs))
      formData.append('note_attrs', JSON.stringify(noteAttrs))
      await apiUpdateImage(editingImage.value.id, formData)
    }

    if (window.showAdminToast) window.showAdminToast('保存成功', 'success')
    closeEditModal()
    await fetchData()
  } catch (e) {
    editError.value = e.message || '保存失败'
  } finally {
    editSaving.value = false
  }
}

function confirmDeleteImage() {
  deleteError.value = ''
  showDeleteConfirm.value = true
}

async function deleteImage() {
  deleting.value = true
  deleteError.value = ''

  try {
    await apiDeleteImage(editingImage.value.id)
    if (window.showAdminToast) window.showAdminToast('图像已删除', 'success')
    showDeleteConfirm.value = false
    closeEditModal()
    await fetchData()
  } catch (e) {
    deleteError.value = e.message || '删除失败'
  } finally {
    deleting.value = false
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
  position: relative;
}

.card-edit-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: rgba(255,255,255,0.9);
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}

.image-card:hover .card-edit-btn {
  opacity: 1;
}

.card-edit-btn:hover {
  background: #3b82f6;
  color: #fff;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-info {
  padding: 12px;
}

.scene-tag, .device-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-right: 6px;
}

.scene-tag { background: #dbeafe; color: #1e40af; }
.device-tag { background: #dcfce7; color: #16a34a; }

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

/* 编辑模态框 */
.edit-image-info {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.edit-preview {
  width: 160px;
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: #e2e8f0;
}

.edit-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.edit-meta {
  flex: 1;
  font-size: 13px;
  color: #374151;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.replace-section {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.replace-section label {
  font-size: 12px;
  color: #64748b;
}

.btn-danger {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: #fef2f2;
  color: #dc2626;
  transition: all 0.2s;
}

.btn-danger:hover:not(:disabled) {
  background: #fee2e2;
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.footer-right {
  display: flex;
  gap: 12px;
  margin-left: auto;
}

.delete-warning {
  color: #92400e;
  font-size: 13px;
  background: #fef3c7;
  padding: 8px 12px;
  border-radius: 6px;
  margin-top: 8px;
}

.file-error {
  color: #dc2626;
  font-size: 12px;
  margin-top: 6px;
  width: 100%;
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
