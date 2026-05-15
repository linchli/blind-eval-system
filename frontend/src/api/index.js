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
    throw new Error('认证已过期')
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

// 场景
export const apiGetScenes = () => request('/api/admin/scenes')
export const apiCreateScene = (data) => request('/api/admin/scenes', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateScene = (id, data) => request(`/api/admin/scenes/${id}`, { method: 'PUT', body: JSON.stringify(data) })

// 机型
export const apiGetModels = () => request('/api/admin/models')
export const apiCreateModel = (data) => request('/api/admin/models', { method: 'POST', body: JSON.stringify(data) })
export const apiUpdateModel = (id, data) => request(`/api/admin/models/${id}`, { method: 'PUT', body: JSON.stringify(data) })

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
export const apiGetRanking = (sceneId) => request(`/api/stats/ranking${sceneId ? '?scene_id=' + sceneId : ''}`)
