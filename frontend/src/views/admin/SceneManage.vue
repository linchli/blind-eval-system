<template>
  <div class="scene-manage-page">
    <div class="page-header">
      <h1 class="page-title">🏞️ 场景管理</h1>
      <button class="btn-primary" @click="showCreateDrawer = true">+ 新增场景</button>
    </div>

    <div class="scene-list">
      <div class="scene-item header">
        <span class="col-category">大类</span>
        <span class="col-subcategory">子类</span>
        <span class="col-name">全名</span>
        <span class="col-folder">目录</span>
        <span class="col-images">图像数</span>
        <span class="col-pairs">配对数</span>
        <span class="col-action">操作</span>
      </div>

      <div v-for="scene in scenes" :key="scene.id" class="scene-item">
        <span class="col-category">{{ scene.category }}</span>
        <span class="col-subcategory">{{ scene.subcategory }}</span>
        <span class="col-name">{{ scene.name }}</span>
        <span class="col-folder">{{ scene.folder_name }}</span>
        <span class="col-images">{{ scene.image_count }}</span>
        <span class="col-pairs">{{ scene.pair_count }}</span>
        <span class="col-action">
          <button class="btn-sm btn-edit" @click="editScene(scene)">编辑</button>
        </span>
      </div>

      <div v-if="scenes.length === 0" class="empty-tip">
        暂无场景，请点击上方按钮创建
      </div>
    </div>

    <!-- 新增/编辑抽屉 -->
    <div v-if="showCreateDrawer || showEditDrawer" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer-content">
        <div class="drawer-header">
          <h2>{{ showEditDrawer ? '编辑场景' : '新增场景' }}</h2>
          <button class="btn-icon" @click="closeDrawer">✕</button>
        </div>

        <div class="drawer-body">
          <div class="form-group">
            <label>大类 (category)</label>
            <select v-model="form.category" @change="updatePreview" class="form-select">
              <option value="">请选择</option>
              <option v-for="cat in categoryOptions" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>子类/时段</label>
            <input v-model="form.subcategory" @input="updatePreview" class="form-input" placeholder="如：白天、傍晚" />
          </div>

          <div class="form-group">
            <label>排序权重</label>
            <input v-model.number="form.sort_order" type="number" class="form-input" />
          </div>

          <div class="preview-box">
            <div class="preview-label">── 自动生成预览 ───</div>
            <div class="preview-item">场景全名： <span class="preview-value">{{ previewName }}</span></div>
            <div class="preview-item">存储目录： <span class="preview-value">{{ previewFolder }}</span></div>
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>

        <div class="drawer-footer">
          <button class="btn-cancel" @click="closeDrawer">取消</button>
          <button class="btn-primary" @click="submitScene" :disabled="saving">
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

const scenes = ref([])
const showCreateDrawer = ref(false)
const showEditDrawer = ref(false)
const editingId = ref(null)
const saving = ref(false)
const errorMessage = ref('')

const categoryOptions = ['池塘', '公园', '街道', '室内', '河流', '森林']

const form = ref({
  category: '',
  subcategory: '',
  sort_order: 100,
})

const previewName = computed(() => {
  if (form.value.category && form.value.subcategory) {
    return `${form.value.category}-${form.value.subcategory}`
  }
  return ''
})

const previewFolder = computed(() => {
  const name = previewName.value.toLowerCase()
  const mapping = {
    '池塘': 'pond', '公园': 'park', '街道': 'street',
    '室内': 'indoor', '河流': 'river', '森林': 'forest',
  }
  const catKey = Object.keys(mapping).find(k => name.includes(k))
  const catEn = catKey ? mapping[catKey] : 'unknown'

  const subEn = form.value.subcategory.toLowerCase().replace(/\s+/g, '_')
  return `scene_${catEn}_${subEn}` || ''
})

function updatePreview() {
  errorMessage.value = ''
}

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

function editScene(scene) {
  editingId.value = scene.id
  form.value = {
    category: scene.category,
    subcategory: scene.subcategory,
    sort_order: scene.sort_order,
  }
  showEditDrawer.value = true
  errorMessage.value = ''
}

function closeDrawer() {
  showCreateDrawer.value = false
  showEditDrawer.value = false
  editingId.value = null
  form.value = { category: '', subcategory: '', sort_order: 100 }
  errorMessage.value = ''
}

async function submitScene() {
  if (!form.value.category || !form.value.subcategory) {
    errorMessage.value = '请填写大类和子类'
    return
  }

  saving.value = true
  errorMessage.value = ''

  try {
    const url = editingId.value ? `/api/admin/scenes/${editingId.value}` : '/api/admin/scenes'
    const method = editingId.value ? 'PUT' : 'POST'

    const body = {
      category: form.value.category,
      subcategory: form.value.subcategory,
      sort_order: form.value.sort_order,
      folder_name: previewFolder.value,
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
    await fetchScenes()
  } catch (e) {
    errorMessage.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchScenes()
})
</script>

<style scoped>
.scene-manage-page {
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

.btn-primary {
  padding: 10px 20px; background: #3b82f6; color: #fff;
  border: none; border-radius: 8px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-cancel {
  padding: 10px 20px; background: #fff; color: #64748b;
  border: 1px solid #e2e8f0; border-radius: 8px;
  font-size: 14px; font-weight: 600; cursor: pointer;
}

.scene-list {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.scene-item {
  display: grid;
  grid-template-columns: 100px 100px 150px 150px 80px 80px 80px;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  align-items: center;
}

.scene-item.header {
  background: #f8fafc;
  font-weight: 600;
  color: #64748b;
}

.col-category, .col-subcategory, .col-name, .col-folder,
.col-images, .col-pairs {
  font-size: 14px;
  color: #374151;
}

.col-name { color: #374151; font-size: 14px; }
.col-folder { color: #374151; ; font-size: 14px; }
.col-action { color: #374151; ; font-size: 14px; }

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
  width: 400px;
  background: white;
  box-shadow: -4px 0 20px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.drawer-header h2 {
  font-size: 16px; margin: 0; color: #1e40af;
}

.btn-icon {
  width: 28px; height: 28px;
  border: none; background: none;
  font-size: 18px; cursor: pointer; color: #64748b;
}

.drawer-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
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

.form-input, .form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #3b82f6;
}

.preview-box {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 16px;
  margin-top: 20px;
}

.preview-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 12px;
}

.preview-item {
  font-size: 13px;
  color: #374151;
  margin-bottom: 8px;
}

.preview-value {
  color: #1e40af;
  font-weight: 600;
  font-family: monospace;
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

@media (max-width: 768px) {
  .drawer-content { width: 100%; }
  .scene-item {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px;
  }
  .scene-item > span { grid-column: auto; }
  .scene-item.header { display: none; }
}
</style>
