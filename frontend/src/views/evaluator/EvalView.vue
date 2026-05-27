<template>
  <div class="eval-page" @click="onPageClick">

    <!-- ===== 顶栏 ===== -->
    <header class="top-bar">
      <div class="bar-left">
        <span class="sys-name">图像盲评</span>
        <button class="help-badge"
                :class="{ 'is-open': helpOpen }"
                @click.stop="helpOpen = !helpOpen"
                title="评测说明">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </button>
      </div>

      <!-- 进度条（IN_SESSION 时显示） -->
      <div class="bar-center" v-if="store.sessionState === 'IN_SESSION'">
        <div class="prog-wrap">
          <div class="prog-bar">
            <div class="prog-fill" :style="{ width: store.sessionProgress + '%' }"></div>
          </div>
          <span class="prog-text">{{ store.sessionScoredCount }} / {{ store.sessionTotalCount }}</span>
        </div>
      </div>

      <div class="bar-right">
        <span class="user-name">{{ authStore.user?.display_name }}</span>
        <button class="btn-sm" @click="handleLogout">退出</button>
      </div>
    </header>

    <!-- ===== 帮助 Popover ===== -->
    <transition name="pop-fade">
      <div v-if="helpOpen" class="help-popover" @click.stop>
        <div class="popover-header">
          <h3>评测说明</h3>
          <button class="popover-close" @click="helpOpen = false">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="popover-body">
          <section class="help-sec">
            <h4>盲评规则</h4>
            <ul>
              <li>仅凭主观观感评分, 整轮提交前均可修改</li>
              <li>提交后结果锁定，无法再修改</li>
              <li>中途退出可继续，评测结果自动保存</li>
            </ul>
          </section>
          <section class="help-sec">
            <h4>图像操作</h4>
            <ul>
              <li>鼠标滚轮：放大 / 缩小图像（双图同步缩放）</li>
              <li>鼠标拖拽：平移查看图像细节</li>
              <li>双击图像：重置缩放与位置</li>
            </ul>
          </section>
        </div>
      </div>
    </transition>

    <!-- ===== 休息建议弹窗 ===== -->
    <transition name="modal-fade">
      <div v-if="showRestConfirm" class="confirm-overlay" @click.self="showRestConfirm = false">
        <div class="confirm-box">
          <h3>温馨提示</h3>
          <p>您今日已评 {{ store.dailyEvaluated }} 对，建议休息后再继续。</p>
          <p class="rest-tip">适当休息可以保证评测质量哦！</p>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="showRestConfirm = false; handleRest()">休息一会</button>
            <button class="btn-confirm" @click="showRestConfirm = false; handleStartAnyway()">继续评测</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ===== 提交确认弹窗 ===== -->
    <transition name="modal-fade">
      <div v-if="showSubmitConfirm" class="confirm-overlay" @click.self="showSubmitConfirm = false">
        <div class="confirm-box">
          <h3>确认提交评测结果</h3>
          <p>提交后所有评分将锁定，无法再修改。请确认已认真完成每一组评测。</p>
          <div class="confirm-stats">
            <div class="stat-item">
              <div class="stat-val">{{ store.sessionScoredCount }}</div>
              <div class="stat-label">已评图对</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{{ store.sessionTotalCount }}</div>
              <div class="stat-label">图对总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{{ store.sessionProgress }}%</div>
              <div class="stat-label">完成率</div>
            </div>
          </div>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="showSubmitConfirm = false">再检查一下</button>
            <button class="btn-confirm" @click="doSubmitRound">确认提交</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ===== 跳过确认弹窗 ===== -->
    <transition name="modal-fade">
      <div v-if="showSkipConfirm" class="confirm-overlay" @click.self="showSkipConfirm = false">
        <div class="confirm-box">
          <h3>确认跳过当前图对</h3>
          <p>当前第 {{ store.cursor + 1 }} 组还未评测，确定要跳过吗？</p>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="showSkipConfirm = false">取消</button>
            <button class="btn-confirm" @click="confirmSkip">确定跳过</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ===== LOADING ===== -->
    <div v-if="store.sessionState === 'LOADING'" class="center-msg">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- ===== NO_PAIRS ===== -->
    <div v-else-if="store.sessionState === 'NO_PAIRS'" class="center-msg">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="#94a3b8" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4m0 4h.01"/>
      </svg>
      <h2>暂无评测数据</h2>
      <p>请管理员先初始化演示数据，或上传图像对</p>
    </div>

    <!-- ===== ALL_DONE ===== -->
    <div v-else-if="store.sessionState === 'ALL_DONE'" class="center-msg finish-box">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
           stroke="#22c55e" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M8 12l3 3 5-6"/>
      </svg>
      <h2>全部完成，感谢参与！</h2>
      <p>您已累计完成 {{ store.totalPairs }} 组图像评价</p>
      <div class="action-buttons">
        <button class="btn-primary" @click="$router.push('/result')">查看结果</button>
        <button class="btn-outline" @click="handleExport">导出CSV</button>
      </div>
    </div>

    <!-- ===== READY_TO_START ===== -->
    <div v-else-if="store.sessionState === 'READY_TO_START'" class="center-msg ready-box">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="#3b82f6" stroke-width="1.5">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      <h2>评测任务准备</h2>
      <p>总剩余待评测图像对：{{ store.remainingCount }} 对</p>
      <div class="action-buttons">
        <button class="btn-primary" @click="handleStart">开始评测</button>
        <button class="btn-sm" @click="handleLogout">退出</button>
      </div>
    </div>

    <!-- ===== RESUMABLE ===== -->
    <div v-else-if="store.sessionState === 'RESUMABLE'" class="center-msg resumable-box">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="#f59e0b" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
      <h2>您有一轮评测进行中</h2>
      <div class="resumable-info" v-if="store.statusInfo?.active_session">
        <p>该轮已评：{{ store.statusInfo.active_session.evaluated_in_session }} / {{ store.statusInfo.active_session.batch_size }} 组</p>
        <div class="mini-progress">
          <div class="mini-progress-bar"
               :style="{ width: (store.statusInfo.active_session.evaluated_in_session / store.statusInfo.active_session.batch_size * 100) + '%' }">
          </div>
        </div>
      </div>
      <p class="tip">评测进度已自动保存，可以继续</p>
      <div class="action-buttons">
        <button class="btn-primary" @click="handleResume">继续评测</button>
        <button class="btn-outline" @click="handleLogout">退出</button>
      </div>
    </div>

    <!-- ===== BATCH_COMPLETE ===== -->
    <div v-else-if="store.sessionState === 'BATCH_COMPLETE'" class="center-msg batch-box">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
           stroke="#22c55e" stroke-width="1.5">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <h2>本轮评测完成！</h2>
      <p>本轮完成：{{ store.sessionTotalCount }} / {{ store.sessionTotalCount }} 组</p>

      <div class="score-dist" v-if="store.roundStats">
        <div class="dist-item">
          <span class="dist-label">A更好</span>
          <span class="dist-val">{{ store.roundStats.score_distribution?.a_much || 0 }}</span>
        </div>
        <div class="dist-item">
          <span class="dist-label">A稍好</span>
          <span class="dist-val">{{ store.roundStats.score_distribution?.a_slight || 0 }}</span>
        </div>
        <div class="dist-item">
          <span class="dist-label">一样好</span>
          <span class="dist-val">{{ store.roundStats.score_distribution?.same || 0 }}</span>
        </div>
        <div class="dist-item">
          <span class="dist-label">B稍好</span>
          <span class="dist-val">{{ store.roundStats.score_distribution?.b_slight || 0 }}</span>
        </div>
        <div class="dist-item">
          <span class="dist-label">B更好</span>
          <span class="dist-val">{{ store.roundStats.score_distribution?.b_much || 0 }}</span>
        </div>
      </div>

      <div class="remaining-info" v-if="store.remainingCount > 0">
        <span class="divider-line"></span>
        <p>还有 {{ store.remainingCount }} 对图像待评测</p>
      </div>

      <div class="action-buttons">
        <button v-if="store.remainingCount > 0" class="btn-primary" @click="handleAnotherRound">再来一轮</button>
        <button class="btn-outline" @click="$router.push('/result')">查看结果</button>
        <button class="btn-sm" @click="handleLogout">休息一会</button>
      </div>
    </div>

    <!-- ===== IN_SESSION ===== -->
    <main v-else-if="store.sessionState === 'IN_SESSION'" class="eval-main">

      <!-- 组信息 + 提交按钮 -->
      <div class="pair-info">
        <div class="pair-info-left">
          <span>第 {{ store.cursor + 1 }} 组 / 共 {{ store.sessionTotalCount }} 组</span>
          <span v-if="store.currentPair?.scene_name" class="scene-tag">
            {{ store.currentPair.scene_name }}
          </span>
          <span v-if="isScored" class="scored-tag">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            已评
          </span>
        </div>
        <button class="submit-btn"
                :class="submitBtnClass"
                :disabled="!store.isAllScored || store.submitted"
                @click="showSubmitConfirm = true">
          <svg v-if="!store.submitted" width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span>{{ store.submitted ? '已提交' : '提交结果' }}</span>
        </button>
      </div>

      <!-- 双图对比 -->
      <div class="compare-area">
        <div class="img-panel" :class="{ selected: lastSide === 'left' }">
          <div class="panel-label">图像 A</div>
          <div class="img-wrap" ref="leftWrapRef">
            <div class="panzoom-target" ref="leftTargetRef">
              <img :src="store.currentPair?.image_a_url" alt="图像A"
                   draggable="false" @load="onImageLoad('left')" />
            </div>
          </div>
          <div class="scale-indicator">
            <span class="scale-value">{{ (currentScale * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="vs-divider"><span>VS</span></div>
        <div class="img-panel" :class="{ selected: lastSide === 'right' }">
          <div class="panel-label">图像 B</div>
          <div class="img-wrap" ref="rightWrapRef">
            <div class="panzoom-target" ref="rightTargetRef">
              <img :src="store.currentPair?.image_b_url" alt="图像B"
                   draggable="false" @load="onImageLoad('right')" />
            </div>
          </div>
          <div class="scale-indicator">
            <span class="scale-value">{{ (currentScale * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>

      <!-- 补充理由 -->
      <div class="comment-row">
        <button class="voice-btn" title="语音输入">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" x2="12" y1="19" y2="22"/>
          </svg>
        </button>
        <label class="comment-label">补充理由</label>
        <input
          class="comment-input"
          type="text"
          v-model="commentText"
          placeholder="选填，可从清晰度/色彩/亮度/噪声/动态人形等方面简述评分依据"
          maxlength="500"
          @blur="saveComment"
        />
        <span class="comment-count" v-if="commentText">{{ commentText.length }}/500</span>
      </div>

      <!-- 底部控制栏 -->
      <div class="score-area">
        <div class="control-row">
          <!-- 上一组 -->
          <button class="nav-btn" :disabled="store.cursor <= 0" @click="handlePrev">
            <svg class="arrow-icon" width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            <span>上一组</span>
          </button>

          <div class="bar-divider"></div>

          <!-- 5 个评分按钮 -->
          <div class="score-group-wrap">
            <!-- 极速评分倒计时 -->
            <div v-if="showCountdown" class="countdown-ring-wrap">
              <svg class="countdown-ring" width="24" height="24" viewBox="0 0 24 24">
                <circle
                  cx="12" cy="12" r="10" fill="none"
                  stroke="#facc15" stroke-width="2"
                  stroke-linecap="round"
                  :stroke-dasharray="62.83"
                  :stroke-dashoffset="62.83 * (countdownProgress / 100)"
                  transform="rotate(-90 12 12)"
                  style="transition: stroke-dashoffset 0.05s linear;"
                />
              </svg>
            </div>
            <!-- 评分修改提示（从按钮上方弹出） -->
            <transition name="score-toast-fade">
              <div v-if="scoreToast.show" class="score-toast" :class="scoreToast.type">
                {{ scoreToast.msg }}
              </div>
            </transition>
            <div class="score-group">
              <button v-for="s in scoreOptions" :key="s.key"
                      class="score-btn"
                      :class="[s.cls, {
                        selected: store.currentScore === s.key,
                        'dimmed': isScored && store.currentScore !== s.key
                      }]"
                      :disabled="!canScore"
                      @click="handleScore(s)">
                {{ s.label }}
              </button>
            </div>
          </div>

          <div class="bar-divider"></div>

          <!-- 下一组 -->
          <button class="nav-btn" :disabled="store.cursor >= store.sessionTotalCount - 1" @click="handleNext">
            <span>下一组</span>
            <svg class="arrow-icon" width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      </div>
    </main>

    <!-- ===== Toast ===== -->
    <div class="toast-container">
      <div v-for="t in store.toasts" :key="t.id" class="toast" :class="t.type">
        {{ t.msg }}
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Panzoom from '@panzoom/panzoom'
import { useAuthStore } from '../../stores/auth.js'
import { useEvalStore } from '../../stores/eval.js'

const router = useRouter()
const authStore = useAuthStore()
const store = useEvalStore()

/* ---- UI 状态 ---- */
const helpOpen = ref(false)
const showRestConfirm = ref(false)
const showSubmitConfirm = ref(false)
const showSkipConfirm = ref(false)
const lastSide = ref('')
const currentScale = ref(1.0)
let autoAdvanceTimer = null

/* ---- 补充理由 ---- */
const commentText = ref('')
const commentSnapshot = ref({})  // 本地快照 { key: comment }，切换图对时用

function getCommentKey() {
  if (!store.currentPair) return null
  return `${store.currentPair.pair_id}_${store.cursor}`
}

function saveComment() {
  const key = getCommentKey()
  if (key && commentText.value) {
    commentSnapshot.value[key] = commentText.value
    store.commentMap[key] = commentText.value
  }
}

function loadComment() {
  const key = getCommentKey()
  if (key) {
    commentText.value = store.commentMap[key] || commentSnapshot.value[key] || ''
  } else {
    commentText.value = ''
  }
}

/* ---- 极速评分倒计时 ---- */
const canScore = ref(false)
const countdownProgress = ref(0)
const showCountdown = ref(false)
let countdownRaf = null

/* ---- 评分修改提示 ---- */
const scoreToast = ref({ show: false, msg: '', type: 'success' })
let scoreToastTimer = null
function showScoreToast(msg, type = 'success') {
  if (scoreToastTimer) clearTimeout(scoreToastTimer)
  scoreToast.value = { show: true, msg, type }
  scoreToastTimer = setTimeout(() => {
    scoreToast.value.show = false
    scoreToastTimer = null
  }, 1500)
}

/* ---- Panzoom ---- */
const leftPanzoom = ref(null)
const rightPanzoom = ref(null)
const leftWrapRef = ref(null)
const rightWrapRef = ref(null)
const leftTargetRef = ref(null)
const rightTargetRef = ref(null)
const isSyncingPan = ref(false)

/* ---- 评分选项 ---- */
const scoreOptions = [
  { key: 'a_much',   label: 'A更好',  cls: 'sc-a-much',   score_a: 2,   score_b: 0 },
  { key: 'a_slight', label: 'A稍好',  cls: 'sc-a-slight', score_a: 1,   score_b: 0 },
  { key: 'same',     label: '一样好', cls: 'sc-same',     score_a: 0.5, score_b: 0.5 },
  { key: 'b_slight', label: 'B稍好',  cls: 'sc-b-slight', score_a: 0,   score_b: 1 },
  { key: 'b_much',   label: 'B更好',  cls: 'sc-b-much',   score_a: 0,   score_b: 2 },
]

/* ---- 计算属性 ---- */
const isScored = computed(() => store.isCurrentScored)

const submitBtnClass = computed(() => {
  if (store.submitted) return 'submitted'
  if (store.isAllScored) return 'ready'
  return ''
})

/* ---- 事件处理 ---- */
async function handleStart() {
  const result = await store.startSession()
  if (result?.needConfirmRest) {
    showRestConfirm.value = true
  }
}

function handleRest() {
  store.resetState()
  authStore.logout()
  router.push('/login')
}

async function handleStartAnyway() {
  await store.forceStartSession()
}

async function handleResume() {
  const result = await store.resumeSession()
  if (!result.success) {
    store.showToast(result.error || '恢复失败', 'error')
  }
}

async function handleAnotherRound() {
  await store.fetchStatus()
  if (store.sessionState === 'READY_TO_START') {
    await handleStart()
  } else if (store.sessionState === 'RESUMABLE') {
    await handleResume()
  }
}

async function handleScore(s) {
  if (isScored.value && store.currentScore === s.key) return

  // 在提交前记录是否为修改评分
  const wasScored = isScored.value

  // 记录侧别
  if (s.key === 'a_much' || s.key === 'a_slight') {
    lastSide.value = 'left'
  } else if (s.key === 'b_much' || s.key === 'b_slight') {
    lastSide.value = 'right'
  } else {
    lastSide.value = ''
  }

  // 保存理由
  saveComment()

  const result = await store.submitScore(s.key, s.label, commentText.value)
  if (result.success) {
    // 仅修改评分时在按钮上方弹出提示，首次评分不弹
    if (wasScored) {
      showScoreToast(`已修改为「${s.label}」`, 'success')
    }

    // 评分后自动跳下一个未评对
    if (autoAdvanceTimer) clearTimeout(autoAdvanceTimer)
    autoAdvanceTimer = setTimeout(() => {
      // 直接在本地计算下一个未评对，避免依赖 computed 属性
      const pairList = store.pairList
      const scoreMap = store.scoreMap
      for (let i = 0; i < pairList.length; i++) {
        const key = `${pairList[i].pair_id}_${i}`
        if (scoreMap[key] === undefined) {
          if (i !== store.cursor) {
            store.goTo(i)
          }
          break
        }
      }
      autoAdvanceTimer = null
    }, 350)
  } else {
    store.showToast(result.error || '提交失败', 'error')
  }
}

function handlePrev() {
  saveComment()
  store.goPrev()
  lastSide.value = ''
}

function handleNext() {
  // 如果当前组未评测，弹窗确认
  if (!isScored.value) {
    showSkipConfirm.value = true
    return
  }
  saveComment()
  store.goNext()
  lastSide.value = ''
}

function confirmSkip() {
  showSkipConfirm.value = false
  saveComment()
  store.goNext()
  lastSide.value = ''
}

async function doSubmitRound() {
  showSubmitConfirm.value = false
  const result = await store.submitRound()
  if (result.success) {
    store.showToast('评测结果已成功提交', 'success')
  } else {
    store.showToast(result.error || '提交失败', 'error')
  }
}

function handleLogout() {
  store.resetState()
  authStore.logout()
  router.push('/login')
}

function handleExport() {
  store.exportCSV()
}

function onPageClick() {
  if (helpOpen.value) helpOpen.value = false
}

/* ---- Panzoom 逻辑 ---- */
function setupWheelHandler(side, panzoomInstance) {
  const target = side === 'left' ? leftTargetRef.value : rightTargetRef.value
  if (!target) return
  const wheelHandler = (e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -1 : 1
    const factor = 0.12
    const scale = panzoomInstance.getScale()
    let newScale = scale + delta * factor
    newScale = Math.min(10, Math.max(0.5, newScale))
    if (newScale !== scale) {
      panzoomInstance.zoom(newScale, { animate: false })
      syncZoom(side, newScale)
    }
  }
  target.addEventListener('wheel', wheelHandler, { passive: false })
  if (side === 'left') leftTargetRef.value._wheelHandler = wheelHandler
  else rightTargetRef.value._wheelHandler = wheelHandler
}

function syncZoom(sourceSide, scale) {
  const targetInstance = sourceSide === 'left' ? rightPanzoom.value : leftPanzoom.value
  if (targetInstance) targetInstance.zoom(scale, { animate: false })
  currentScale.value = scale
}

function syncPan(sourceSide, x, y) {
  if (isSyncingPan.value) return
  isSyncingPan.value = true
  const targetInstance = sourceSide === 'left' ? rightPanzoom.value : leftPanzoom.value
  if (targetInstance) targetInstance.pan(x, y, { animate: false })
  // 使用 setTimeout 延迟重置标志位，确保同一帧内的事件被正确忽略
  setTimeout(() => { isSyncingPan.value = false }, 0)
}

function destroyPanzoom(side) {
  const instance = side === 'left' ? leftPanzoom.value : rightPanzoom.value
  if (instance?.destroy) instance.destroy()
  const target = side === 'left' ? leftTargetRef.value : rightTargetRef.value
  if (target?._wheelHandler) {
    target.removeEventListener('wheel', target._wheelHandler)
    delete target._wheelHandler
  }
  if (target?._panHandler) {
    target.removeEventListener('panzoompan', target._panHandler)
    delete target._panHandler
  }
  if (side === 'left') leftPanzoom.value = null
  else rightPanzoom.value = null
}

async function initPanzoom(side) {
  const target = side === 'left' ? leftTargetRef.value : rightTargetRef.value
  const container = side === 'left' ? leftWrapRef.value : rightWrapRef.value
  if (!target || !container) return
  const img = target.querySelector('img')
  if (!img || !img.complete || img.naturalWidth === 0) return
  destroyPanzoom(side)
  const panzoom = new Panzoom(target, {
    minScale: 0.5, maxScale: 10, wheel: false,
    pinchAndPan: true, cursor: 'grab', zoomDoubleTapSpeed: 0,
  })
  setupWheelHandler(side, panzoom)
  const panHandler = (e) => {
    if (!isSyncingPan.value) {
      syncPan(side, e.detail.x, e.detail.y)
    }
  }
  target.addEventListener('panzoompan', panHandler)
  if (side === 'left') leftTargetRef.value._panHandler = panHandler
  else rightTargetRef.value._panHandler = panHandler
  target.addEventListener('dblclick', (e) => {
    e.stopPropagation()
    // 先禁用同步，避免重置过程中触发同步
    isSyncingPan.value = true
    panzoom.reset()
    syncZoom(side, 1)
    const otherInstance = side === 'left' ? rightPanzoom.value : leftPanzoom.value
    if (otherInstance) otherInstance.reset()
    // 延迟恢复同步
    setTimeout(() => { isSyncingPan.value = false }, 0)
  })
  if (side === 'left') leftPanzoom.value = panzoom
  else rightPanzoom.value = panzoom
  currentScale.value = 1
}

function onImageLoad(side) { nextTick(() => initPanzoom(side)) }

function ensurePanzoom() {
  if (leftTargetRef.value?.querySelector('img')?.complete) initPanzoom('left')
  if (rightTargetRef.value?.querySelector('img')?.complete) initPanzoom('right')
}

watch(() => store.currentPair?.pair_id, async () => {
  lastSide.value = ''
  destroyPanzoom('left')
  destroyPanzoom('right')
  await nextTick()
  ensurePanzoom()
  loadComment()
})

// 极速评分倒计时
watch(() => store.currentPair?.pair_id, () => {
  canScore.value = false
  showCountdown.value = true
  countdownProgress.value = 0

  if (countdownRaf) cancelAnimationFrame(countdownRaf)

  const startTime = Date.now()
  const duration = 1500

  function tick() {
    const elapsed = Date.now() - startTime
    countdownProgress.value = Math.min(100, (elapsed / duration) * 100)

    if (elapsed >= duration) {
      canScore.value = true
      setTimeout(() => { showCountdown.value = false }, 300)
    } else {
      countdownRaf = requestAnimationFrame(tick)
    }
  }
  countdownRaf = requestAnimationFrame(tick)
}, { immediate: true })

/* ---- 生命周期 ---- */
onMounted(async () => {
  await store.fetchStatus()
  setTimeout(ensurePanzoom, 200)
})

onUnmounted(() => {
  destroyPanzoom('left')
  destroyPanzoom('right')
  if (autoAdvanceTimer) clearTimeout(autoAdvanceTimer)
  if (countdownRaf) cancelAnimationFrame(countdownRaf)
})
</script>

<style scoped>
/* ========================================
   基础布局
   ======================================== */
.eval-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f5ff;
  position: relative;
}

/* ===== 顶栏 ===== */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: #fff;
  border-bottom: 2px solid #dbeafe;
  box-shadow: 0 1px 4px rgba(59,130,246,0.06);
  position: relative;
  z-index: 50;
}
.bar-left { display: flex; align-items: center; gap: 8px; }
.sys-name { font-size: 16px; font-weight: 700; color: #1e40af; }

.help-badge {
  width: 26px; height: 26px;
  border-radius: 6px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #3b82f6;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.help-badge:hover { background: #dbeafe; border-color: #93c5fd; color: #2563eb; }
.help-badge.is-open { background: #dbeafe; border-color: #3b82f6; color: #1d4ed8; }

.bar-center { flex: 1; max-width: 400px; margin: 0 24px; }
.prog-wrap { display: flex; align-items: center; gap: 10px; }
.prog-bar { flex: 1; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.prog-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 3px;
  transition: width 0.4s;
}
.prog-text { font-size: 12px; color: #64748b; white-space: nowrap; }
.bar-right { display: flex; align-items: center; gap: 10px; }
.user-name { font-size: 13px; color: #475569; }
.btn-sm {
  padding: 5px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #fff; color: #64748b; font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.btn-sm:hover { border-color: #3b82f6; color: #3b82f6; }

/* ===== 帮助 Popover ===== */
.help-popover {
  position: absolute;
  top: 50px;
  left: 24px;
  width: 340px;
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(59,130,246,0.12), 0 2px 8px rgba(0,0,0,0.06);
  z-index: 100;
  overflow: hidden;
}
.popover-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.popover-header h3 { font-size: 13px; font-weight: 600; color: #1e40af; }
.popover-close {
  width: 22px; height: 22px; border-radius: 4px;
  border: none; background: transparent; color: #94a3b8;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.popover-close:hover { background: #f1f5f9; color: #475569; }

.popover-body { padding: 14px 16px 18px; max-height: 400px; overflow-y: auto; }
.popover-body::-webkit-scrollbar { width: 4px; }
.popover-body::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }

.help-sec { margin-bottom: 14px; }
.help-sec:last-child { margin-bottom: 0; }
.help-sec h4 {
  font-size: 11px; font-weight: 600; color: #3b82f6;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.help-sec ul { list-style: none; padding: 0; }
.help-sec li {
  font-size: 12px; line-height: 1.7; color: #475569;
  padding-left: 12px; position: relative;
}
.help-sec li::before {
  content: ''; position: absolute; left: 0; top: 9px;
  width: 4px; height: 4px; border-radius: 50%; background: #94a3b8;
}

/* ===== 主区域 ===== */
.eval-main {
  flex: 1; padding: 16px 24px;
  display: flex; flex-direction: column;
}

/* ===== 状态卡片通用样式 ===== */
.center-msg {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  padding: 40px;
}
.center-msg h2 { font-size: 22px; color: #1e40af; margin: 0; }
.center-msg p { color: #64748b; margin: 0; }

.action-buttons { display: flex; gap: 12px; margin-top: 16px; }
.btn-primary {
  padding: 10px 28px; background: #3b82f6; color: #fff;
  border: none; border-radius: 10px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.btn-primary:hover { background: #2563eb; }
.btn-outline {
  padding: 10px 28px; background: #fff; color: #3b82f6;
  border: 2px solid #3b82f6; border-radius: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.btn-outline:hover { background: #eff6ff; }

/* ===== READY_TO_START 卡片 ===== */
.ready-box .tip { font-size: 13px; color: #94a3b8; margin-top: 4px; }

/* ===== RESUMABLE 卡片 ===== */
.resumable-box .tip { font-size: 13px; color: #94a3b8; margin-top: 4px; }
.resumable-info { margin: 16px 0; text-align: center; }
.resumable-info p { margin: 8px 0; }
.mini-progress {
  width: 200px; height: 8px; background: #e2e8f0;
  border-radius: 4px; overflow: hidden; margin: 8px auto 0;
}
.mini-progress-bar {
  height: 100%; background: linear-gradient(90deg, #f59e0b, #fbbf24);
  border-radius: 4px; transition: width 0.3s;
}

/* ===== BATCH_COMPLETE 卡片 ===== */
.batch-box { background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%); }
.score-dist {
  display: flex; gap: 12px; margin: 20px 0;
  padding: 16px 24px; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 10px;
}
.dist-item { display: flex; flex-direction: column; align-items: center; }
.dist-label { font-size: 11px; color: #64748b; }
.dist-val { font-size: 20px; font-weight: 700; color: #1e40af; }
.remaining-info { text-align: center; margin: 16px 0; }
.divider-line {
  display: block; width: 100px; height: 2px;
  background: #e2e8f0; margin: 0 auto 16px;
}

/* ===== 完成卡片 ===== */
.finish-box { background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%); }
.finish-box h2 { color: #16a34a; }

/* ===== 组信息行 + 提交按钮 ===== */
.pair-info {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.pair-info-left {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #475569;
}
.scene-tag {
  background: #dbeafe; color: #1d4ed8;
  padding: 2px 10px; border-radius: 6px;
  font-size: 12px; font-weight: 500;
}
.scored-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: #dcfce7; color: #16a34a;
  padding: 2px 10px; border-radius: 6px;
  font-size: 12px; font-weight: 500;
}

/* ===== 提交结果按钮 ===== */
.submit-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 18px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.25s; white-space: nowrap;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #94a3b8;
}
.submit-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.submit-btn.ready {
  border: 1px solid #86efac;
  background: #f0fdf4;
  color: #16a34a;
  animation: submitPulse 2s ease-in-out infinite;
}
@keyframes submitPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
  50%      { box-shadow: 0 0 10px 2px rgba(34,197,94,0.18); }
}
.submit-btn.ready:hover { background: #dcfce7; border-color: #4ade80; color: #15803d; }
.submit-btn.submitted { border: 1px solid #86efac; background: #f0fdf4; color: #16a34a; cursor: default; }

/* ===== 双图对比 ===== */
.compare-area { flex: 1; display: flex; gap: 12px; min-height: 0;max-height: calc(100vh - 250px);}
.img-panel {
  flex: 1; display: flex; flex-direction: column;
  background: #fff; border-radius: 12px;
  border: 2px solid #e2e8f0; overflow: hidden;
  transition: border-color 0.2s;
}
.img-panel.selected { border-color: #3b82f6; }
.panel-label {
  padding: 8px; text-align: center;
  font-size: 13px; font-weight: 600; color: #64748b;
  background: #f8fafc; border-bottom: 1px solid #e2e8f0;
}
.img-wrap { flex: 1; position: relative; overflow: hidden; background: #f1f5f9; cursor: grab; }
.img-wrap:active { cursor: grabbing; }
.panzoom-target {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%;
  will-change: transform; transform-origin: center center;
}
.panzoom-target img {
  max-width: 100%; max-height: 100%;
  object-fit: contain; user-select: none;
}
.vs-divider {
  display: flex; align-items: center; justify-content: center;
  width: 40px; flex-shrink: 0;
}
.vs-divider span {
  width: 36px; height: 36px; border-radius: 50%;
  background: #dbeafe; color: #2563eb;
  font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.scale-indicator { padding: 6px 12px; text-align: center; }
.scale-value { font-size: 13px; font-weight: 500; color: #64748b; }

/* ===== 底部控制栏 ===== */
.score-area { margin-top: 12px; }

/* ===== 补充理由 ===== */
.comment-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 6px 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}
.voice-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 6px;
  border: none; background: transparent;
  color: #94a3b8; cursor: pointer;
  flex-shrink: 0; transition: all 0.2s;
}
.voice-btn:hover { background: #f1f5f9; color: #3b82f6; }
.comment-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}
.comment-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  color: #334155;
  background: transparent;
  padding: 4px 0;
}
.comment-input::placeholder { color: #94a3b8; }
.comment-count {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}
.control-row {
  display: flex; align-items: center; justify-content: center; gap: 0;
}
.bar-divider { width: 1px; height: 28px; background: #e2e8f0; margin: 0 14px; flex-shrink: 0; }

/* ===== 导航按钮 ===== */
.nav-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 18px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
  white-space: nowrap; flex-shrink: 0;
}
.nav-btn .arrow-icon { transition: transform 0.2s ease; }
.nav-btn:hover:not(:disabled) { background: #eff6ff; border-color: #93c5fd; color: #3b82f6; }
.nav-btn:first-child:hover:not(:disabled) .arrow-icon { transform: translateX(-2px); }
.nav-btn:last-child:hover:not(:disabled) .arrow-icon { transform: translateX(2px); }
.nav-btn:active:not(:disabled) { background: #dbeafe; transform: scale(0.97); }
.nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ===== 评分按钮组 ===== */
.score-group-wrap { position: relative; flex-shrink: 0; }
.score-group { display: flex; gap: 4px; }
.score-btn {
  padding: 12px 24px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #334155; font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
  min-width: 96px; text-align: center;
}
.sc-a-much:hover { border-color: #2563eb; background: #eff6ff; color: #2563eb; }
.sc-a-slight:hover { border-color: #60a5fa; background: #f0f7ff; color: #3b82f6; }
.sc-same:hover { border-color: #94a3b8; background: #f8fafc; color: #475569; }
.sc-b-slight:hover { border-color: #fb923c; background: #fff7ed; color: #ea580c; }
.sc-b-much:hover { border-color: #f97316; background: #fff7ed; color: #ea580c; }

.sc-a-much.selected { border-color: #2563eb; background: #dbeafe; color: #1d4ed8; box-shadow: 0 0 10px rgba(37,99,235,0.18); }
.sc-a-slight.selected { border-color: #60a5fa; background: #eff6ff; color: #2563eb; box-shadow: 0 0 10px rgba(96,165,250,0.15); }
.sc-same.selected { border-color: #94a3b8; background: #f1f5f9; color: #334155; box-shadow: 0 0 10px rgba(148,163,184,0.15); }
.sc-b-slight.selected { border-color: #fb923c; background: #ffedd5; color: #c2410c; box-shadow: 0 0 10px rgba(251,146,60,0.18); }
.sc-b-much.selected { border-color: #f97316; background: #ffedd5; color: #c2410c; box-shadow: 0 0 10px rgba(249,115,22,0.18); }

/* 已评分时未选中按钮：降低不透明度但保留hover和可点击 */
.score-btn.dimmed { opacity: 0.45; }
.score-btn.dimmed:hover { opacity: 0.85; }
.score-btn:disabled { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
.score-btn:active:not(.selected) { transform: scale(0.96); }

/* ===== 评分修改提示（按钮上方弹出） ===== */
.score-toast {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px; font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  z-index: 50;
}
.score-toast.success { background: rgba(220,252,231,0.95); border: 1px solid #86efac; color: #15803d; box-shadow: 0 4px 12px rgba(22,163,74,0.12); }
.score-toast.error { background: rgba(254,226,226,0.95); border: 1px solid #fca5a5; color: #dc2626; box-shadow: 0 4px 12px rgba(220,38,38,0.12); }
.score-toast-fade-enter-active { transition: all 0.25s ease; }
.score-toast-fade-leave-active { transition: all 0.2s ease; }
.score-toast-fade-enter-from { opacity: 0; transform: translateX(-50%) translateY(6px); }
.score-toast-fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(-4px); }

/* ===== 加载 / 错误 ===== */
.spinner {
  width: 32px; height: 32px;
  border: 3px solid #dbeafe; border-top-color: #3b82f6;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== 提交确认弹窗 ===== */
.confirm-overlay {
  position: fixed; inset: 0;
  background: rgba(15,23,42,0.45);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
}
.confirm-box {
  width: 400px; background: #fff;
  border: 1px solid #dbeafe; border-radius: 14px;
  padding: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.confirm-box h3 { font-size: 16px; font-weight: 600; color: #1e40af; margin-bottom: 10px; }
.confirm-box p { font-size: 13px; color: #475569; line-height: 1.6; }
.rest-tip { color: #94a3b8 !important; font-size: 12px !important; margin-top: 8px !important; }
.confirm-stats {
  display: flex; gap: 16px; margin: 18px 0;
  padding: 14px; background: #f8fafc;
  border-radius: 8px; border: 1px solid #e2e8f0;
}
.stat-item { flex: 1; text-align: center; }
.stat-val  { font-size: 22px; font-weight: 700; color: #1e40af; }
.stat-label { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.confirm-actions { display: flex; gap: 10px; margin-top: 20px; }
.confirm-actions button {
  flex: 1; padding: 10px 0; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel { background: #f8fafc; border: 1px solid #e2e8f0; color: #64748b; }
.btn-cancel:hover { background: #f1f5f9; color: #334155; }
.btn-confirm { background: #f0fdf4; border: 1px solid #86efac; color: #16a34a; }
.btn-confirm:hover { background: #dcfce7; border-color: #4ade80; color: #15803d; box-shadow: 0 0 12px rgba(34,197,94,0.12); }

/* ===== Toast ===== */
.toast-container {
  position: fixed; top: 20px; left: 50%;
  transform: translateX(-50%); z-index: 300;
  display: flex; flex-direction: column; gap: 8px;
  pointer-events: none;
}
.toast {
  padding: 10px 22px; border-radius: 8px;
  font-size: 13px; font-weight: 500;
  animation: toastIn 0.3s ease, toastOut 0.3s ease 1.7s forwards;
  backdrop-filter: blur(8px);
}
.toast.info { background: rgba(219,234,254,0.92); border: 1px solid #93c5fd; color: #1d4ed8; }
.toast.success { background: rgba(220,252,231,0.92); border: 1px solid #86efac; color: #15803d; }
.toast.error { background: rgba(254,226,226,0.92); border: 1px solid #fca5a5; color: #dc2626; }
@keyframes toastIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes toastOut { from { opacity: 1; } to { opacity: 0; transform: translateY(-8px); } }

/* ===== 动画 ===== */
.pop-fade-enter-active { transition: all 0.2s ease; }
.pop-fade-leave-active { transition: all 0.15s ease; }
.pop-fade-enter-from, .pop-fade-leave-to { opacity: 0; transform: translateY(-6px) scale(0.97); }
.modal-fade-enter-active { transition: all 0.2s ease; }
.modal-fade-leave-active { transition: all 0.15s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-from .confirm-box, .modal-fade-leave-to .confirm-box { transform: scale(0.96) translateY(8px); }

/* ===== 极速评分倒计时 ===== */
.countdown-ring-wrap {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
}
.countdown-ring {
  display: block;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .compare-area { flex-direction: column; }
  .vs-divider { width: auto; height: 32px; }
  .score-btn { padding: 10px 14px; min-width: 70px; font-size: 13px; }
  .nav-btn { padding: 8px 12px; font-size: 12px; }
  .bar-divider { margin: 0 8px; }
  .top-bar { padding: 8px 12px; }
  .eval-main { padding: 10px 12px; }
  .help-popover { width: 290px; left: 12px; }
  .score-dist { flex-wrap: wrap; justify-content: center; }
  .comment-row { flex-wrap: wrap; }
  .comment-input { min-width: 0; }
}
</style>
