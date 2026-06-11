<template>
  <div class="user-manage">
    <div class="page-header">
      <h2>用户管理</h2>
    </div>

    <!-- 用户列表 -->
    <div class="card">
      <div class="user-list">
        <div class="user-item header">
          <span class="col-id">ID</span>
          <span class="col-username">用户名</span>
          <span class="col-email">邮箱</span>
          <span class="col-role">角色</span>
          <span class="col-eval">已评价</span>
          <span class="col-active">最后活跃</span>
          <span class="col-status">状态</span>
          <span class="col-actions">操作</span>
        </div>
        <div v-for="user in paginatedUsers" :key="user.id" class="user-item">
          <span class="col-id">{{ user.id }}</span>
          <span class="col-username">{{ user.username }}</span>
          <span class="col-email">{{ user.email }}</span>
          <span class="col-role">
            <span class="role-tag" :class="user.role">{{ roleLabels[user.role] || user.role }}</span>
          </span>
          <span class="col-eval">
            <span class="eval-count" :class="{ zero: user.evaluation_count === 0 }">{{ user.evaluation_count }}</span>
          </span>
          <span class="col-active">{{ formatTime(user.last_active_at) }}</span>
          <span class="col-status">
            <span v-if="user.has_active_reset" class="status-tag resetting">重置中</span>
            <span v-else class="status-tag active">正常</span>
          </span>
          <span class="col-actions">
            <button class="btn-action" @click="handleResetPassword(user)">重置密码</button>
          </span>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="users.length > 0" class="pagination">
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
        <span class="page-info">共 {{ users.length }} 条，{{ currentPage }}/{{ totalPages }} 页</span>
        <div class="page-btns">
          <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
          <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
        </div>
      </div>
    </div>

    <!-- 确认重置弹窗 -->
    <div v-if="showConfirmModal" class="modal-overlay" @click.self="showConfirmModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>确认重置密码</h3>
          <button class="btn-close" @click="showConfirmModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>确定要重置用户 <strong>{{ selectedUser?.username }}</strong> 的密码吗？</p>
          <p class="hint">重置后将生成一个重置链接，您需要将链接发送给用户，用户可自行设置新密码。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showConfirmModal = false">取消</button>
          <button class="btn-primary" @click="confirmReset" :disabled="loading">
            {{ loading ? '生成中...' : '确认重置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 重置链接弹窗 -->
    <div v-if="showLinkModal" class="modal-overlay" @click.self="showLinkModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>密码重置链接已生成</h3>
          <button class="btn-close" @click="showLinkModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>请将以下链接发送给用户 <strong>{{ selectedUser?.username }}</strong>：</p>
          <div class="link-box">
            <input type="text" :value="resetLink" readonly ref="linkInput" />
            <button class="btn-copy" @click="copyLink">复制</button>
          </div>
          <p class="hint">链接有效期：{{ expiresIn }}</p>
          <p class="hint">用户访问此链接后可自行设置新密码。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="showLinkModal = false">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetUsers, apiTriggerResetPassword } from '../../api/index.js'

const authStore = useAuthStore()

const users = ref([])
const loading = ref(false)
const showConfirmModal = ref(false)
const showLinkModal = ref(false)
const selectedUser = ref(null)
const resetLink = ref('')
const expiresIn = ref('')
const linkInput = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = computed(() => Math.max(1, Math.ceil(users.value.length / pageSize.value)))
const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return users.value.slice(start, start + pageSize.value)
})

const roleLabels = {
  admin: '管理员',
  evaluator: '评测员',
  guest: '访客',
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date

  if (diff < 0) return '刚刚'
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  return date.toLocaleDateString('zh-CN')
}

async function loadUsers() {
  try {
    users.value = await apiGetUsers()
  } catch (e) {
    window.showAdminToast?.(e.message || '加载用户列表失败', 'error')
  }
}

function handleResetPassword(user) {
  selectedUser.value = user
  showConfirmModal.value = true
}

async function confirmReset() {
  if (!selectedUser.value) return
  loading.value = true
  try {
    const result = await apiTriggerResetPassword(selectedUser.value.id)
    resetLink.value = window.location.origin + result.reset_link
    expiresIn.value = result.expires_in
    showConfirmModal.value = false
    showLinkModal.value = true
    await loadUsers() // 刷新状态
  } catch (e) {
    window.showAdminToast?.(e.message || '重置密码失败', 'error')
  } finally {
    loading.value = false
  }
}

function copyLink() {
  if (linkInput.value) {
    linkInput.value.select()
    navigator.clipboard.writeText(linkInput.value.value).then(() => {
      window.showAdminToast?.('链接已复制', 'success')
    }).catch(() => {
      // fallback
      document.execCommand('copy')
      window.showAdminToast?.('链接已复制', 'success')
    })
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.user-manage {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
}

.user-list {
  overflow-x: auto;
}

.user-item {
  display: grid;
  grid-template-columns: 50px 100px 160px 80px 70px 120px 80px 100px;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.user-item.header {
  background: #f8fafc;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.user-item:not(.header):hover {
  background: #f8fafc;
}

.col-id { color: #94a3b8; font-size: 13px; }
.col-username { font-weight: 500; color: #1e293b; }
.col-email { color: #475569; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-eval { text-align: center; }
.col-active { color: #64748b; font-size: 13px; }

.eval-count {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: #dbeafe;
  color: #1e40af;
}

.eval-count.zero {
  background: #f1f5f9;
  color: #94a3b8;
}

.role-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.role-tag.admin { background: #dbeafe; color: #1e40af; }
.role-tag.evaluator { background: #dcfce7; color: #16a34a; }
.role-tag.guest { background: #f1f5f9; color: #64748b; }

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-tag.active { background: #dcfce7; color: #16a34a; }
.status-tag.resetting { background: #fef3c7; color: #d97706; }

.btn-action {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #3b82f6;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-action:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 480px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
}

.modal-body {
  padding: 24px;
}

.modal-body p {
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
}

.modal-body strong {
  color: #1e293b;
}

.hint {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 8px;
}

.link-box {
  display: flex;
  gap: 8px;
  margin: 16px 0;
}

.link-box input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #1e293b;
  background: #f8fafc;
}

.btn-copy {
  padding: 10px 16px;
  border: 1px solid #3b82f6;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-copy:hover {
  background: #2563eb;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
}

.btn-cancel {
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #64748b;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel:hover {
  border-color: #94a3b8;
}

.btn-primary {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
