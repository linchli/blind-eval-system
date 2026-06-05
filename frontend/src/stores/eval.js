/**
 * 评测状态管理 Store - 完整状态机实现
 *
 * 状态流转：
 * LOADING → NO_PAIRS | READY_TO_START | RESUMABLE | ALL_DONE
 * READY_TO_START → IN_SESSION (开始评测)
 * RESUMABLE → IN_SESSION (继续评测)
 * IN_SESSION → BATCH_COMPLETE (全部评完)
 * BATCH_COMPLETE → ALL_DONE (提交后无剩余) | READY_TO_START → IN_SESSION (再来一轮)
 * ALL_DONE → READY_TO_START (管理员新增图片)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  apiGetEvalStatus,
  apiStartSession,
  apiResumeSession,
  apiSubmitDraft,
  apiSubmitRound,
  apiExportCSV
} from '../api/index.js'

export const useEvalStore = defineStore('eval', () => {
  // ==================== 状态定义 ====================
  // sessionState: 'LOADING' | 'NO_PAIRS' | 'READY_TO_START' | 'RESUMABLE' | 'IN_SESSION' | 'BATCH_COMPLETE' | 'ALL_DONE'
  const sessionState = ref('LOADING')

  // ==================== 状态信息 ====================
  // statusInfo: /api/eval/status 返回的完整数据
  const statusInfo = ref(null)

  // ==================== 会话信息 ====================
  const sessionInfo = ref(null)  // { session_id, batch_size }
  const pairList = ref([])       // 当前 session 的图对列表（全量）
  const cursor = ref(0)          // 当前游标（0 ~ pairList.length-1）
  const scoreMap = ref({})       // { pairId: scoreKey }
  const commentMap = ref({})     // { pairId: comment }
  const submitted = ref(false)    // 当前 session 是否已提交

  // ==================== 统计信息 ====================
  const roundStats = ref(null)   // 提交后的统计 { total_evaluated, remaining_count, score_distribution }

  // ==================== UI 状态 ====================
  const loading = ref(false)
  const error = ref('')
  const toasts = ref([])
  let toastId = 0

  // ==================== 计算属性 ====================

  // 总图对数
  const totalPairs = computed(() => statusInfo.value?.total_pairs || 0)

  // 已提交数
  const evaluatedCount = computed(() => statusInfo.value?.evaluated_count || 0)

  // 剩余未评数
  const remainingCount = computed(() => statusInfo.value?.remaining_count || 0)

  // 当前图对
  const currentPair = computed(() => pairList.value[cursor.value] || null)

  // 当前图对是否已评分
  const isCurrentScored = computed(() => {
    if (!currentPair.value) return false
    const key = `${currentPair.value.pair_id}_${cursor.value}`
    return scoreMap.value[key] !== undefined
  })

  // 当前评分
  const currentScore = computed(() => {
    if (!currentPair.value) return null
    const key = `${currentPair.value.pair_id}_${cursor.value}`
    return scoreMap.value[key] || null
  })

  // Session 内已评数
  const sessionScoredCount = computed(() => {
    return Object.keys(scoreMap.value).length
  })

  // Session 内总数
  const sessionTotalCount = computed(() => pairList.value.length)

  // Session 内进度
  const sessionProgress = computed(() => {
    if (!sessionTotalCount.value) return 0
    return Math.round((sessionScoredCount.value / sessionTotalCount.value) * 100)
  })

  // 是否全部评完
  const isAllScored = computed(() => {
    return pairList.value.length > 0 && sessionScoredCount.value >= pairList.value.length
  })

  // 下一个未评对的游标
  const nextUnscoredCursor = computed(() => {
    for (let i = 0; i < pairList.value.length; i++) {
      const key = `${pairList.value[i].pair_id}_${i}`
      if (scoreMap.value[key] === undefined) {
        return i
      }
    }
    return pairList.value.length - 1
  })

  // 建议休息
  const suggestRest = computed(() => statusInfo.value?.suggest_rest || false)

  // 今日已评
  const dailyEvaluated = computed(() => statusInfo.value?.daily_evaluated || 0)

  // ==================== 核心方法 ====================

  /**
   * 获取评测状态
   * 进入页面时调用，根据返回的 status 决定 UI
   */
  async function fetchStatus() {
    loading.value = true
    error.value = ''
    try {
      const data = await apiGetEvalStatus()
      statusInfo.value = data

      // 根据 status 字段更新 sessionState
      switch (data.status) {
        case 'no_pairs':
          sessionState.value = 'NO_PAIRS'
          break
        case 'all_done':
          sessionState.value = 'ALL_DONE'
          break
        case 'resumable':
          sessionState.value = 'RESUMABLE'
          break
        case 'ready':
          sessionState.value = 'READY_TO_START'
          break
        default:
          sessionState.value = 'READY_TO_START'
      }
    } catch (e) {
      error.value = e.message
      sessionState.value = 'NO_PAIRS'
    } finally {
      loading.value = false
    }
  }

  /**
   * 开始新会话
   * 点击"开始评测"时调用
   */
  async function startSession() {
    if (suggestRest.value) {
      // 需要先确认
      return { needConfirmRest: true }
    }
    return await forceStartSession()
  }

  async function forceStartSession() {
    loading.value = true
    error.value = ''
    try {
      const data = await apiStartSession()
      sessionInfo.value = {
        session_id: data.session_id,
        batch_size: data.batch_size
      }

      // 初始化状态
      pairList.value = data.pairs
      cursor.value = 0
      scoreMap.value = {}
      commentMap.value = {}
      submitted.value = false
      roundStats.value = null

      // 从 pairs 中提取已有评分和理由（使用 pair_id + 索引作为 key）
      for (let i = 0; i < data.pairs.length; i++) {
        const pair = data.pairs[i]
        const key = `${pair.pair_id}_${i}`
        if (pair.my_score) {
          scoreMap.value[key] = pair.my_score
        }
        if (pair.comment) {
          commentMap.value[key] = pair.comment
        }
      }

      // 定位到第一个未评对
      cursor.value = nextUnscoredCursor.value

      sessionState.value = 'IN_SESSION'

      // 刷新状态
      await fetchStatus()

      return { success: true }
    } catch (e) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 恢复会话
   * 点击"继续评测"时调用
   */
  async function resumeSession() {
    loading.value = true
    error.value = ''
    try {
      const data = await apiResumeSession()
      sessionInfo.value = {
        session_id: data.session_id,
        batch_size: data.batch_size
      }

      // 初始化状态
      pairList.value = data.pairs
      scoreMap.value = {}
      commentMap.value = {}
      submitted.value = false
      roundStats.value = null

      // 从 pairs 中提取已有评分和理由（使用 pair_id + 索引作为 key）
      for (let i = 0; i < data.pairs.length; i++) {
        const pair = data.pairs[i]
        const key = `${pair.pair_id}_${i}`
        if (pair.my_score) {
          scoreMap.value[key] = pair.my_score
        }
        if (pair.comment) {
          commentMap.value[key] = pair.comment
        }
      }

      // 定位到下一个未评对
      cursor.value = data.next_cursor

      sessionState.value = 'IN_SESSION'

      return { success: true }
    } catch (e) {
      error.value = e.message
      // 如果没有进行中的会话，重新获取状态
      await fetchStatus()
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * 根据 cursor 位置计算 is_repeat
   * 统计当前 pair_id 在 cursor 位置之前出现的次数
   */
  function calcIsRepeat(pairList, cursor) {
    const pairId = pairList[cursor].pair_id
    let count = 0
    for (let i = 0; i <= cursor; i++) {
      if (pairList[i].pair_id === pairId) count++
    }
    return count > 1 ? 1 : 0
  }

  /**
   * 提交单个评分（草稿）
   * @param {string} score - 评分键值
   * @param {string} scoreLabel - 评分标签
   * @param {string} comment - 评价理由
   */
  async function submitScore(score, scoreLabel, comment = '') {
    if (!currentPair.value || !sessionInfo.value) return

    const pairId = currentPair.value.pair_id
    const key = `${pairId}_${cursor.value}`
    const isRepeat = calcIsRepeat(pairList.value, cursor.value)

    try {
      await apiSubmitDraft({
        pair_id: pairId,
        session_id: sessionInfo.value.session_id,
        score: score,
        score_label: scoreLabel,
        is_repeat: isRepeat,
        comment: comment
      })

      // 立即更新本地状态（使用 pair_id + 索引作为 key，避免重复图对覆盖）
      scoreMap.value[key] = score

      // 全部评完后仍保持 IN_SESSION，让用户自己点击"提交结果"
      // BATCH_COMPLETE 仅在 submitRound 提交整轮后触发

      return { success: true }
    } catch (e) {
      error.value = e.message
      return { success: false, error: e.message }
    }
  }

  /**
   * 提交整轮
   * 点击"提交结果"时调用
   */
  async function submitRound() {
    if (!sessionInfo.value || !isAllScored.value) return

    loading.value = true
    error.value = ''
    try {
      const data = await apiSubmitRound(sessionInfo.value.session_id)
      submitted.value = true
      roundStats.value = data

      // 刷新状态
      await fetchStatus()

      // 检查是否全部完成
      if (remainingCount.value === 0) {
        sessionState.value = 'ALL_DONE'
      } else {
        sessionState.value = 'BATCH_COMPLETE'
      }

      return { success: true, data }
    } catch (e) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  // ==================== 导航方法 ====================

  function goPrev() {
    if (cursor.value > 0) {
      cursor.value--
    }
  }

  function goNext() {
    if (cursor.value < pairList.value.length - 1) {
      cursor.value++
    }
  }

  function goTo(index) {
    if (index >= 0 && index < pairList.value.length) {
      cursor.value = index
    }
  }

  // ==================== Toast ====================

  function showToast(msg, type = 'info') {
    const id = ++toastId
    toasts.value.push({ id, msg, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 2500)
  }

  // ==================== 重置 ====================

  function resetState() {
    sessionState.value = 'LOADING'
    statusInfo.value = null
    sessionInfo.value = null
    pairList.value = []
    cursor.value = 0
    scoreMap.value = {}
    commentMap.value = {}
    submitted.value = false
    roundStats.value = null
    error.value = ''
  }

  // ==================== 导出 ====================

  async function exportCSV() {
    try {
      const resp = await apiExportCSV()
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `盲评结果_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.csv`
      a.click()
      URL.revokeObjectURL(url)
      showToast('导出成功', 'success')
    } catch (e) {
      showToast('导出失败: ' + e.message, 'error')
    }
  }

  // ==================== 返回 ====================

  return {
    // 状态
    sessionState,
    statusInfo,
    sessionInfo,
    pairList,
    cursor,
    scoreMap,
    commentMap,
    submitted,
    roundStats,
    loading,
    error,
    toasts,

    // 计算属性
    totalPairs,
    evaluatedCount,
    remainingCount,
    currentPair,
    isCurrentScored,
    currentScore,
    sessionScoredCount,
    sessionTotalCount,
    sessionProgress,
    isAllScored,
    suggestRest,
    dailyEvaluated,

    // 核心方法
    fetchStatus,
    startSession,
    forceStartSession,
    resumeSession,
    submitScore,
    submitRound,

    // 导航
    goPrev,
    goNext,
    goTo,

    // 工具
    showToast,
    resetState,
    exportCSV
  }
})