<template>
  <div class="reset-password-page">
    <div class="reset-card">
      <h1 class="title">重置密码</h1>

      <!-- 验证中 -->
      <div v-if="verifying" class="loading-state">
        <div class="spinner"></div>
        <p>正在验证重置链接...</p>
      </div>

      <!-- 链接无效 -->
      <div v-else-if="!tokenValid" class="error-state">
        <div class="error-icon">✕</div>
        <p class="error-msg">{{ errorMsg }}</p>
        <button class="btn-primary" @click="goToLogin">返回登录</button>
      </div>

      <!-- 重置表单 -->
      <div v-else-if="!resetSuccess" class="form-state">
        <p class="subtitle">为用户 <strong>{{ username }}</strong> 设置新密码</p>

        <div class="form-group">
          <label>新密码</label>
          <input
            type="password"
            v-model="newPassword"
            placeholder="请输入新密码（至少6位）"
            :class="{ error: errors.newPassword }"
          />
          <span v-if="errors.newPassword" class="error-text">{{ errors.newPassword }}</span>
        </div>

        <div class="form-group">
          <label>确认密码</label>
          <input
            type="password"
            v-model="confirmPassword"
            placeholder="请再次输入新密码"
            :class="{ error: errors.confirmPassword }"
          />
          <span v-if="errors.confirmPassword" class="error-text">{{ errors.confirmPassword }}</span>
        </div>

        <div v-if="submitError" class="submit-error">{{ submitError }}</div>

        <button class="btn-primary" @click="handleSubmit" :disabled="submitting">
          {{ submitting ? '提交中...' : '确认重置' }}
        </button>
      </div>

      <!-- 重置成功 -->
      <div v-else class="success-state">
        <div class="success-icon">✓</div>
        <p class="success-msg">密码重置成功！</p>
        <p class="hint">请使用新密码登录</p>
        <button class="btn-primary" @click="goToLogin">前往登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiVerifyResetToken, apiResetPassword } from '../../api/index.js'

const route = useRoute()
const router = useRouter()

const verifying = ref(true)
const tokenValid = ref(false)
const username = ref('')
const errorMsg = ref('')

const newPassword = ref('')
const confirmPassword = ref('')
const errors = ref({ newPassword: '', confirmPassword: '' })
const submitError = ref('')
const submitting = ref(false)
const resetSuccess = ref(false)

const token = route.query.token

async function verifyToken() {
  if (!token) {
    verifying.value = false
    errorMsg.value = '无效的重置链接'
    return
  }

  try {
    const result = await apiVerifyResetToken(token)
    tokenValid.value = true
    username.value = result.username
  } catch (e) {
    errorMsg.value = e.message || '重置链接无效或已过期'
  } finally {
    verifying.value = false
  }
}

function validate() {
  errors.value = { newPassword: '', confirmPassword: '' }
  let valid = true

  if (newPassword.value.length < 6) {
    errors.value.newPassword = '密码长度至少6位'
    valid = false
  }

  if (newPassword.value !== confirmPassword.value) {
    errors.value.confirmPassword = '两次输入的密码不一致'
    valid = false
  }

  return valid
}

async function handleSubmit() {
  if (!validate()) return

  submitting.value = true
  submitError.value = ''

  try {
    await apiResetPassword({
      token,
      new_password: newPassword.value,
    })
    resetSuccess.value = true
  } catch (e) {
    submitError.value = e.message || '重置失败，请重试'
  } finally {
    submitting.value = false
  }
}

function goToLogin() {
  router.push('/login')
}

onMounted(verifyToken)
</script>

<style scoped>
.reset-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f5ff;
  padding: 20px;
}

.reset-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  padding: 40px;
  width: 400px;
  max-width: 100%;
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
  margin-bottom: 24px;
}

.subtitle {
  font-size: 14px;
  color: #64748b;
  text-align: center;
  margin-bottom: 24px;
}

.subtitle strong {
  color: #1e293b;
}

/* Loading */
.loading-state {
  text-align: center;
  padding: 40px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: #64748b;
  font-size: 14px;
}

/* Error */
.error-state {
  text-align: center;
  padding: 40px 0;
}

.error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fef2f2;
  color: #dc2626;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.error-msg {
  color: #dc2626;
  font-size: 14px;
  margin-bottom: 24px;
}

/* Form */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.15s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group input.error {
  border-color: #dc2626;
}

.error-text {
  display: block;
  font-size: 12px;
  color: #dc2626;
  margin-top: 4px;
}

.submit-error {
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  margin-bottom: 16px;
  padding: 10px;
  background: #fef2f2;
  border-radius: 8px;
}

/* Success */
.success-state {
  text-align: center;
  padding: 40px 0;
}

.success-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #dcfce7;
  color: #16a34a;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.success-msg {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.hint {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 24px;
}

/* Button */
.btn-primary {
  width: 100%;
  padding: 12px;
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
</style>
