/**
 * API 客户端 - 完整 API
 */
const API_BASE = ''

async function request(url, options = {}) {
  const token = localStorage.getItem('blind_eval_token')
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(`${API_BASE}${url}`, { ...options, headers })

  if (resp.status === 401) {
    localStorage.removeItem('blind_eval_token')
    localStorage.removeItem('blind_eval_user')
    window.location.hash = '#/login'
    throw new Error('用户名或密码错误')
  }
  if (!resp.ok) {
    const d = await resp.json().catch(() => ({}))
    throw new Error(d.detail || `请求失败 (${resp.status})`)
  }
  if (resp.headers.get('content-type')?.includes('text/csv')) return resp
  return resp.json()
}

// ==================== 认证 ====================
export const apiLogin = (data) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(data) })
export const apiRegister = (data) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) })
export const apiGetMe = () => request('/api/auth/me')

// ==================== 管理后台 ====================

// 大类
export const apiGetCategories = () => request('/api/admin/categories')
export const apiCreateCategory = (data) => request('/api/admin/categories', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateCategory = (id, data) => request(`/api/admin/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const apiDeleteCategory = (id) => request(`/api/admin/categories/${id}`, { method: 'DELETE' })

// 子类
export const apiGetSubcategories = () => request('/api/admin/subcategories')
export const apiCreateSubcategory = (data) => request('/api/admin/subcategories', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateSubcategory = (id, data) => request(`/api/admin/subcategories/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const apiDeleteSubcategory = (id) => request(`/api/admin/subcategories/${id}`, { method: 'DELETE' })

// 场景
export const apiGetScenes = () => request('/api/admin/scenes')
export const apiCreateScene = (data) => request('/api/admin/scenes', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateScene = (id, data) => request(`/api/admin/scenes/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const apiDeleteScene = (id) => request(`/api/admin/scenes/${id}`, { method: 'DELETE' })

// 设备
export const apiGetDevices = () => request('/api/admin/devices')
export const apiCreateDevice = (data) => request('/api/admin/devices', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateDevice = (id, data) => request(`/api/admin/devices/${id}`, { method: 'PUT', body: JSON.stringify(data) })

// 图像
export const apiGetImages = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/admin/images${query ? '?' + query : ''}`)
}
export const apiUploadImage = (formData) => request('/api/admin/images', {
  method: 'POST',
  body: formData,
  headers: {}, // 让浏览器自动设置 Content-Type
})
export const apiDeleteImage = (id) => request(`/api/admin/images/${id}`, { method: 'DELETE' })

// 配对
export const apiGetPairs = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/admin/pairs${query ? '?' + query : ''}`)
}
export const apiPreviewPairs = (data) => request('/api/admin/pairs/preview', { method: 'POST', body: JSON.stringify(data) })
export const apiGeneratePairs = (data) => request('/api/admin/pairs/generate', { method: 'POST', body: JSON.stringify(data) })
export const apiGetSceneStats = (sceneId) => request(`/api/admin/pairs/scene-stats/${sceneId}`)

// 概览
export const apiGetOverview = () => request('/api/admin/overview')

// 用户管理
export const apiGetUsers = () => request('/api/admin/users')
export const apiTriggerResetPassword = (userId) => request(`/api/admin/users/${userId}/reset-password`, { method: 'PUT' })

// 密码重置（无需认证）
export const apiVerifyResetToken = (token) => request(`/api/auth/verify-reset-token?token=${token}`)
export const apiResetPassword = (data) => request('/api/auth/reset-password', { method: 'POST', body: JSON.stringify(data) })

// ==================== 评测核心 API ====================

export const apiGetEvalStatus = () => request('/api/eval/status')
export const apiStartSession = () => request('/api/eval/start-session', { method: 'POST' })
export const apiResumeSession = () => request('/api/eval/resume-session', { method: 'POST' })
export const apiSubmitDraft = (data) => request('/api/eval/submit', { method: 'POST', body: JSON.stringify(data) })
export const apiSubmitRound = (sessionId) => request('/api/eval/submit-round', {
  method: 'POST',
  body: JSON.stringify({ session_id: sessionId })
})
export const apiGetPairDetail = (pairId) => request(`/api/eval/pair/${pairId}`)

// ==================== 兼容旧 API ====================
export const apiGetProgress = (sceneId) => request(`/api/eval/progress${sceneId ? '?scene_id=' + sceneId : ''}`)
export const apiGetMyEvals = () => request('/api/eval/my')
export const apiExportCSV = () => request('/api/eval/export/csv')

// ==================== 统计 ====================
export const apiStatsOverview = () => request('/api/stats/overview')
export const apiDataCleaning = (sceneId) => request(`/api/stats/cleaning${sceneId ? '?scene_id=' + sceneId : ''}`)

// ==================== 排行榜 API ====================

export const apiGetRanking = (sceneId) =>
  request(`/api/ranking/list${sceneId ? '?scene_id=' + sceneId : ''}`)

export const apiGetDeviceRanking = (deviceId) =>
  request(`/api/ranking/device/${deviceId}`)

export const apiGetRankingReport = () =>
  request('/api/ranking/report')

export const apiRunCleaning = (sceneId) =>
  request(`/api/ranking/clean-layer2${sceneId ? '?scene_id=' + sceneId : ''}`, { method: 'POST' })

export const apiGetSessionPairs = (sessionId) =>
  request(`/api/ranking/session/${sessionId}/pairs`)

export const apiGetDeviceWinRate = (deviceId) =>
  request(`/api/ranking/device/${deviceId}/winrate`)

export const apiGetSceneCompare = (sceneIds) =>
  request(`/api/ranking/compare?scene_ids=${sceneIds.join(',')}`)
