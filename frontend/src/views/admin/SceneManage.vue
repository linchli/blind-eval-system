<template>
  <div class="scene-manage-page">
    <div class="page-header">
      <h1 class="page-title">场景管理</h1>
      <div class="header-actions">
        <button class="btn-secondary" @click="showCategoryManager = true">大类管理</button>
        <button class="btn-secondary" @click="showSubcategoryManager = true">子类管理</button>
        <button class="btn-primary" @click="openCreateDrawer">+ 新增场景</button>
      </div>
    </div>

    <!-- 场景列表 -->
    <div class="scene-list">
      <div class="scene-item header">
        <span class="col-category filterable" @click.stop="toggleFilter('category')">
          大类
          <span class="filter-icon" :class="{ active: filters.category }">▼</span>
          <div v-if="activeFilter === 'category'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.category" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.category }" @click="setFilter('category', '')">全部</div>
              <div v-for="val in filteredCategoryOptions" :key="val" class="filter-option" :class="{ selected: filters.category === val }" @click="setFilter('category', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-location filterable" @click.stop="toggleFilter('location')">
          地点
          <span class="filter-icon" :class="{ active: filters.location }">▼</span>
          <div v-if="activeFilter === 'location'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.location" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.location }" @click="setFilter('location', '')">全部</div>
              <div v-for="val in filteredLocationOptions" :key="val" class="filter-option" :class="{ selected: filters.location === val }" @click="setFilter('location', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-subcategory filterable" @click.stop="toggleFilter('subcategory')">
          子类
          <span class="filter-icon" :class="{ active: filters.subcategory }">▼</span>
          <div v-if="activeFilter === 'subcategory'" class="filter-dropdown" @click.stop>
            <input v-model="filterSearch.subcategory" placeholder="搜索..." class="filter-search" />
            <div class="filter-list">
              <div class="filter-option" :class="{ selected: !filters.subcategory }" @click="setFilter('subcategory', '')">全部</div>
              <div v-for="val in filteredSubcategoryOptions" :key="val" class="filter-option" :class="{ selected: filters.subcategory === val }" @click="setFilter('subcategory', val)">{{ val }}</div>
            </div>
          </div>
        </span>
        <span class="col-folder">目录</span>
        <span class="col-images">图像数</span>
        <span class="col-pairs">配对数</span>
        <span class="col-action">操作</span>
      </div>

      <div v-for="scene in paginatedScenes" :key="scene.id" class="scene-item">
        <span class="col-category">{{ scene.category_name }}</span>
        <span class="col-location">{{ scene.location || '-' }}</span>
        <span class="col-subcategory">{{ scene.subcategory_name }}</span>
        <span class="col-folder" :title="scene.folder_name">{{ scene.folder_name }}</span>
        <span class="col-images">{{ scene.image_count }}</span>
        <span class="col-pairs">{{ scene.pair_count }}</span>
        <span class="col-action">
          <button class="btn-sm btn-edit" @click="editScene(scene)">编辑</button>
          <button class="btn-sm btn-delete" @click="deleteScene(scene)">删除</button>
        </span>
      </div>

      <div v-if="filteredScenes.length === 0" class="empty-tip">
        暂无场景，请先创建大类与子类
      </div>

      <!-- 分页 -->
      <div v-if="filteredScenes.length > 0" class="pagination">
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
        <span class="page-info">共 {{ filteredScenes.length }} 条，{{ currentPage }}/{{ totalPages }} 页</span>
        <div class="page-btns">
          <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
          <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
        </div>
      </div>
    </div>

    <!-- 新增/编辑场景抽屉 -->
    <div v-if="showCreateDrawer || showEditDrawer" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer-content">
        <div class="drawer-header">
          <h2>{{ showEditDrawer ? '编辑场景' : '新增场景' }}</h2>
          <button class="btn-icon" @click="closeDrawer">✕</button>
        </div>

        <div class="drawer-body">
          <div class="form-group">
            <label>大类</label>
            <select v-model="form.category_id" @change="updatePreview" class="form-select" :disabled="showEditDrawer">
              <option value="" disabled selected>请选择大类</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}({{ cat.location || '默认' }})
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>子类</label>
            <select v-model="form.subcategory_id" @change="updatePreview" class="form-select" :disabled="showEditDrawer">
              <option value="" disabled selected>请选择子类</option>
              <option v-for="sub in subcategories" :key="sub.id" :value="sub.id">
                {{ sub.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>排序权重</label>
            <input v-model.number="form.sort_order" type="number" class="form-input" />
          </div>

          <div class="preview-box">
            <div class="preview-label">── 场景预览 ───</div>
            <div class="preview-item">场景全名： <span class="preview-value">{{ previewName }}</span></div>
            <div class="preview-item">存储目录： <span class="preview-value">{{ previewFolder }}</span></div>
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>

        <div class="drawer-footer">
          <button class="btn-cancel" @click="closeDrawer">取消</button>
          <button class="btn-primary" @click="submitScene" :disabled="saving">
            {{ saving ? '保存中...' : '确认' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 大类管理弹窗 -->
    <div v-if="showCategoryManager" class="drawer-overlay" @click.self="showCategoryManager = false">
      <div class="drawer-content">
        <div class="drawer-header">
          <h2>大类管理</h2>
          <button class="btn-icon" @click="showCategoryManager = false">✕</button>
        </div>
        <div class="drawer-body">
          <div class="inline-form">
            <input v-model="catForm.name" placeholder="大类名" class="form-input" />
            <input v-model="catForm.location" placeholder="地点（可选）" class="form-input" />
            <button class="btn-primary btn-sm" @click="addCategory">新增</button>
          </div>
          <div class="sub-list">
            <div v-for="cat in categories" :key="cat.id" class="sub-list-item">
              <span>{{ cat.name }}({{ cat.location || '-' }})</span>
              <span class="badge">{{ cat.scene_count }} 场景</span>
              <button class="btn-sm btn-delete" @click="deleteCategory(cat)">删除</button>
            </div>
            <div v-if="categories.length === 0" class="empty-tip">暂无大类</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 子类管理弹窗 -->
    <div v-if="showSubcategoryManager" class="drawer-overlay" @click.self="showSubcategoryManager = false">
      <div class="drawer-content">
        <div class="drawer-header">
          <h2>子类管理</h2>
          <button class="btn-icon" @click="showSubcategoryManager = false">✕</button>
        </div>
        <div class="drawer-body">
          <div class="inline-form">
            <input v-model="subForm.name" placeholder="子类名" class="form-input" />
            <button class="btn-primary btn-sm" @click="addSubcategory">新增</button>
          </div>
          <div class="sub-list">
            <div v-for="sub in subcategories" :key="sub.id" class="sub-list-item">
              <span>{{ sub.name }}</span>
              <span class="badge">{{ sub.scene_count }} 场景</span>
              <button class="btn-sm btn-delete" @click="deleteSubcategory(sub)">删除</button>
            </div>
            <div v-if="subcategories.length === 0" class="empty-tip">暂无子类</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  apiGetScenes, apiCreateScene, apiUpdateScene, apiDeleteScene,
  apiGetCategories, apiCreateCategory, apiDeleteCategory,
  apiGetSubcategories, apiCreateSubcategory, apiDeleteSubcategory,
} from '../../api/index.js'

const scenes = ref([])
const categories = ref([])
const subcategories = ref([])
const showCreateDrawer = ref(false)
const showEditDrawer = ref(false)
const showCategoryManager = ref(false)
const showSubcategoryManager = ref(false)
const editingId = ref(null)
const saving = ref(false)
const errorMessage = ref('')

// 分页和筛选
const activeFilter = ref(null)
const filters = ref({ category: '', location: '', subcategory: '' })
const filterSearch = ref({ category: '', location: '', subcategory: '' })
const currentPage = ref(1)
const pageSize = ref(10)

const form = ref({
  category_id: '',
  subcategory_id: '',
  sort_order: 100,
})

const catForm = ref({ name: '', location: '' })
const subForm = ref({ name: '' })

const previewName = computed(() => {
  if (!form.value.category_id || !form.value.subcategory_id) return ''
  const cat = categories.value.find(c => c.id === form.value.category_id)
  const sub = subcategories.value.find(s => s.id === form.value.subcategory_id)
  if (!cat || !sub) return ''
  const loc = cat.location ? `(${cat.location})` : ''
  return `${cat.name}${loc}-${sub.name}`
})

const previewFolder = computed(() => {
  return form.value.category_id && form.value.subcategory_id ? '创建后自动分配' : ''
})

// 筛选和分页逻辑
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

// 唯一值列表
const uniqueCategories = computed(() => [...new Set(scenes.value.map(s => s.category_name))].sort())
const uniqueLocations = computed(() => [...new Set(scenes.value.map(s => s.location || '-'))].sort())
const uniqueSubcategories = computed(() => [...new Set(scenes.value.map(s => s.subcategory_name))].sort())

// 搜索过滤后的选项
const filteredCategoryOptions = computed(() => {
  const search = filterSearch.value.category.toLowerCase()
  if (!search) return uniqueCategories.value
  return uniqueCategories.value.filter(v => v.toLowerCase().includes(search))
})
const filteredLocationOptions = computed(() => {
  const search = filterSearch.value.location.toLowerCase()
  if (!search) return uniqueLocations.value
  return uniqueLocations.value.filter(v => v.toLowerCase().includes(search))
})
const filteredSubcategoryOptions = computed(() => {
  const search = filterSearch.value.subcategory.toLowerCase()
  if (!search) return uniqueSubcategories.value
  return uniqueSubcategories.value.filter(v => v.toLowerCase().includes(search))
})

// 筛选后的数据
const filteredScenes = computed(() => {
  return scenes.value.filter(scene => {
    if (filters.value.category && scene.category_name !== filters.value.category) return false
    if (filters.value.location && (scene.location || '-') !== filters.value.location) return false
    if (filters.value.subcategory && scene.subcategory_name !== filters.value.subcategory) return false
    return true
  })
})

// 分页
const totalPages = computed(() => Math.max(1, Math.ceil(filteredScenes.value.length / pageSize.value)))
const paginatedScenes = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredScenes.value.slice(start, start + pageSize.value)
})

function updatePreview() {
  errorMessage.value = ''
}

async function fetchAll() {
  const [scenesData, catsData, subsData] = await Promise.all([
    apiGetScenes(),
    apiGetCategories(),
    apiGetSubcategories(),
  ])
  scenes.value = scenesData
  categories.value = catsData
  subcategories.value = subsData
}

function openCreateDrawer() {
  editingId.value = null
  form.value = { category_id: '', subcategory_id: '', sort_order: 100 }
  showCreateDrawer.value = true
  showEditDrawer.value = false
  errorMessage.value = ''
}

function editScene(scene) {
  editingId.value = scene.id
  form.value = {
    category_id: scene.category_id,
    subcategory_id: scene.subcategory_id,
    sort_order: scene.sort_order,
  }
  showEditDrawer.value = true
  showCreateDrawer.value = false
  errorMessage.value = ''
}

function closeDrawer() {
  showCreateDrawer.value = false
  showEditDrawer.value = false
  editingId.value = null
  form.value = { category_id: '', subcategory_id: '', sort_order: 100 }
  errorMessage.value = ''
}

async function submitScene() {
  if (!form.value.category_id || !form.value.subcategory_id) {
    errorMessage.value = '请选择大类和子类'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    if (editingId.value) {
      await apiUpdateScene(editingId.value, { sort_order: form.value.sort_order })
    } else {
      await apiCreateScene({
        category_id: form.value.category_id,
        subcategory_id: form.value.subcategory_id,
        sort_order: form.value.sort_order,
      })
    }
    closeDrawer()
    await fetchAll()
  } catch (e) {
    errorMessage.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function deleteScene(scene) {
  if (!confirm(`确定删除场景 "${scene.category_name}(${scene.location})-${scene.subcategory_name}"？`)) return
  try {
    await apiDeleteScene(scene.id)
    await fetchAll()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

async function addCategory() {
  if (!catForm.value.name) return alert('请输入大类名')
  try {
    await apiCreateCategory({
      name: catForm.value.name,
      location: catForm.value.location || '',
    })
    catForm.value = { name: '', location: '' }
    await fetchAll()
  } catch (e) {
    alert(e.message || '创建失败')
  }
}

async function deleteCategory(cat) {
  if (cat.scene_count > 0) {
    alert(`大类 "${cat.name}(${cat.location})" 下有 ${cat.scene_count} 个场景，请先删除场景`)
    return
  }
  if (!confirm(`确定删除大类 "${cat.name}(${cat.location})"？`)) return
  try {
    await apiDeleteCategory(cat.id)
    await fetchAll()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

async function addSubcategory() {
  if (!subForm.value.name) return alert('请输入子类名')
  try {
    await apiCreateSubcategory({ name: subForm.value.name })
    subForm.value = { name: '' }
    await fetchAll()
  } catch (e) {
    alert(e.message || '创建失败')
  }
}

async function deleteSubcategory(sub) {
  if (sub.scene_count > 0) {
    alert(`子类 "${sub.name}" 下有 ${sub.scene_count} 个场景，请先删除场景`)
    return
  }
  if (!confirm(`确定删除子类 "${sub.name}"？`)) return
  try {
    await apiDeleteSubcategory(sub.id)
    await fetchAll()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

onMounted(() => {
  fetchAll()
  document.addEventListener('click', closeAllFilters)
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
.header-actions {
  display: flex;
  gap: 8px;
}
.btn-secondary {
  padding: 10px 20px;
  background: #fff;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-secondary:hover { background: #eff6ff; }
.btn-cancel {
  padding: 10px 20px;
  background: #fff;
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-sm {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
}
.btn-primary {
  padding: 10px 20px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}
.scene-list {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  overflow: hidden;
}
.scene-item {
  display: grid;
  grid-template-columns: 100px 100px 100px 120px 80px 80px 120px;
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
.col-category, .col-location, .col-subcategory, .col-folder, .col-images, .col-pairs {
  font-size: 14px;
  color: #374151;
}
.col-folder {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
}
.col-action {
  display: flex;
  gap: 6px;
}
.btn-edit:hover { background: #eff6ff; border-color: #3b82f6; color: #3b82f6; }
.btn-delete:hover { background: #fef2f2; border-color: #ef4444; color: #ef4444; }
.empty-tip {
  grid-column: 1 / -1;
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 14px;
}

/* 抽屉 */
.drawer-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0,0,0,.5);
  display: flex;
  justify-content: flex-end;
  z-index: 100;
}
.drawer-content {
  width: 420px;
  background: white;
  box-shadow: -4px 0 20px rgba(0,0,0,.1);
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
.drawer-header h2 { font-size: 16px; margin: 0; color: #1e40af; }
.btn-icon {
  width: 28px; height: 28px;
  border: none; background: none;
  font-size: 18px; cursor: pointer;
  color: #64748b;
}
.drawer-body { padding: 20px; flex: 1; overflow-y: auto; }
.drawer-footer {
  display: flex; justify-content: flex-end; gap: 12px;
  padding: 16px 20px; border-top: 1px solid #e2e8f0;
}
.form-group { margin-bottom: 20px; }
.form-group label {
  display: block; font-size: 13px; font-weight: 500;
  color: #374151; margin-bottom: 8px;
}
.form-input, .form-select {
  width: 100%; padding: 10px 12px;
  border: 1px solid #e2e8f0; border-radius: 6px;
  font-size: 14px; box-sizing: border-box;
}
.form-input:focus, .form-select:focus {
  outline: none; border-color: #3b82f6;
}
.preview-box {
  background: #f0f9ff; border-radius: 8px;
  padding: 16px; margin-top: 20px;
}
.preview-label { font-size: 12px; color: #64748b; margin-bottom: 12px; }
.preview-item { font-size: 13px; color: #374151; margin-bottom: 8px; }
.preview-value { color: #1e40af; font-weight: 600; font-family: monospace; }
.error-message { color: #dc2626; font-size: 13px; margin-top: 12px; }

/* 管理弹窗 */
.inline-form {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
}
.inline-form .form-input { flex: 1; }
.sub-list { border-top: 1px solid #f1f5f9; }
.sub-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
}
.sub-list-item span { flex: 1; }
.badge {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
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
</style>
