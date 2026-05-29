<template>
  <div class="batch-upload">
    <h1>批量上传</h1>
    <p class="page-description">根据指定文件夹结构，批量新增场景、新增设备、上传图像</p>

    <!-- 步骤条 -->
    <div class="steps-bar">
      <div class="step" :class="{ active: step === 1, done: step > 1 }">
        <span class="step-num">{{ step > 1 ? '✓' : '1' }}</span>
        <span class="step-label">选择文件夹</span>
      </div>
      <div class="step-line" :class="{ active: step > 1 }"></div>
      <div class="step" :class="{ active: step === 2, done: step > 2 }">
        <span class="step-num">{{ step > 2 ? '✓' : '2' }}</span>
        <span class="step-label">预览确认</span>
      </div>
      <div class="step-line" :class="{ active: step > 2 }"></div>
      <div class="step" :class="{ active: step === 3 || step === 4 }">
        <span class="step-num">{{ step === 4 ? '✓' : '3' }}</span>
        <span class="step-label">上传结果</span>
      </div>
    </div>

    <!-- ========== 步骤 1: 选择文件夹 ========== -->
    <div v-if="step === 1" class="step-content">
      <div class="help-card">
        <h3>使用说明</h3>
        <pre class="help-structure">your_folder/
├── images/                      ← 图像根目录
│   ├── 车库(B4)-白天/           ← 场景文件夹
│   │   ├── 632-WB4.jpg          ← 设备名.jpg
│   │   ├── 632-WB4.json         ← 元信息(可选)
│   │   └── 732-WB4.jpg
│   └── 天台(32楼)-低照/
│       ├── 632-WB4.jpg
│       └── 832-WB4.jpg
└── devices.json                ← 设备参数(可选)</pre>
        <div class="help-rules">
          <p><strong>场景命名规则:</strong> 场景大类(地点)-子类</p>
          <p>示例: 车库(B4)-白天 → 大类=车库, 地点=B4, 子类=白天</p>
          <p><strong>模式说明:</strong></p>
          <p>· 严格模式: 根目录有 devices.json，设备参数从该文件读取</p>
          <p>· 宽松模式: 根目录无 devices.json，自动从图像文件名提取设备(不推荐使用)</p>
        </div>
      </div>

      <div class="folder-select-zone" @click="$refs.folderInput.click()">
        <input ref="folderInput" type="file" webkitdirectory multiple
               @change="onFolderSelected" style="display:none" />
        <div class="zone-icon">📁</div>
        <div class="zone-text">点击选择文件夹</div>
        <div class="zone-hint">选择包含 images/ 子目录的文件夹</div>
      </div>
    </div>

    <!-- ========== 步骤 2: 预览确认 ========== -->
    <div v-if="step === 2" class="step-content">
      <div class="scan-result">
        <div class="result-header">
          <span class="mode-badge" :class="scanData.mode">
            {{ scanData.mode === 'strict' ? '🔒 严格模式' : '🔓 宽松模式' }}
          </span>
          <span class="mode-desc">
            {{ scanData.mode === 'strict' ? '检测到 devices.json' : '未检测到 devices.json' }}
          </span>
        </div>

        <!-- 场景列表 -->
        <div class="scene-list">
          <div class="section-title">场景文件夹 ({{ scanData.scenes.length }}个)</div>
          <div v-for="(scene, si) in scanData.scenes" :key="scene.name" class="scene-item">
            <div class="scene-header" @click="toggleScene(si)">
              <span class="scene-toggle">{{ expandedScenes[si] ? '▼' : '▶' }}</span>
              <span class="scene-name">{{ scene.name }}</span>
              <span class="scene-stats">{{ scene.imageCount }}张图像, {{ scene.metaCount }}个元信息</span>
            </div>
            <div v-if="expandedScenes[si]" class="file-list">
              <div class="file-row header-row">
                <span class="file-col-img">图像</span>
                <span class="file-col-meta">元信息</span>
              </div>
              <div v-for="pair in scene.filePairs" :key="pair.img" class="file-row">
                <span class="file-col-img">{{ pair.img }} {{ pair.hasMeta ? '✓' : '' }}</span>
                <span class="file-col-meta" :class="{ 'no-meta': !pair.hasMeta }">{{ pair.meta || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 设备列表 -->
        <div v-if="scanData.devices.length > 0" class="device-section">
          <div class="section-title device-title" @click="toggleDevices">
            <span>{{ expandedDevices ? '▼' : '▶' }}</span>
            设备列表 ({{ scanData.devices.length }}个 · {{ scanData.mode === 'strict' ? '从 devices.json 读取' : '从图像文件名提取' }})
          </div>
          <div v-if="expandedDevices" class="device-table">
            <div class="device-row header">
              <span>设备名</span>
              <span>主控型号</span>
              <span>光圈</span>
              <span>焦距</span>
            </div>
            <div v-for="d in scanData.devices" :key="d.设备名" class="device-row">
              <span>{{ d.设备名 }}</span>
              <span>{{ d.主控型号 || '-' }}</span>
              <span>{{ d.光圈 || '-' }}</span>
              <span>{{ d.焦距 || '-' }}</span>
            </div>
          </div>
        </div>

        <div v-if="scanData.errors.length > 0" class="errors">
          <div class="errors-title">⚠ 存在以下问题，请修复后重新上传：</div>
          <div v-for="(e, i) in scanData.errors" :key="i" class="error-msg">{{ e }}</div>
        </div>

        <div class="step-actions">
          <button class="btn-secondary" @click="goStep1">重新选择</button>
          <button class="btn-primary" :disabled="scanData.errors.length > 0" @click="goStep3">
            {{ scanData.errors.length > 0 ? '请先修复上述问题' : '开始上传 →' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ========== 步骤 3: 上传进度 ========== -->
    <div v-if="step === 3" class="step-content">
      <div class="progress-card">
        <div class="section-title">上传进度</div>
        <div class="progress-bar-wrap">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: overallPercent + '%' }"></div>
          </div>
          <div class="progress-label">{{ completedScenes }}/{{ totalScenes }} 场景完成</div>
        </div>
        <div v-if="currentScene" class="current-scene">
          当前: {{ currentScene }}
          <div class="progress-bar small">
            <div class="progress-fill" :style="{ width: currentPercent + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="result-card">
        <div class="section-title">上传结果</div>
        <table class="result-table">
          <thead><tr><th>场景</th><th>上传</th><th>跳过</th><th>错误</th><th>状态</th></tr></thead>
          <tbody>
            <template v-for="(r, i) in uploadResults" :key="i">
              <tr>
                <td>{{ r.scene_name }}</td>
                <td>{{ r.uploaded }}</td>
                <td>{{ r.skipped }}</td>
                <td>{{ r.errors.length }}</td>
                <td>
                  <span v-if="r.status === 'done' && r.errors.length === 0" class="status-ok">✓</span>
                  <span v-else-if="r.status === 'done' && r.errors.length > 0" class="status-err">✗</span>
                  <span v-else-if="r.status === 'uploading'" class="status-ing">⏳</span>
                  <span v-else class="status-wait">⏸</span>
                </td>
              </tr>
              <tr v-if="r.status === 'done' && r.errors.length > 0" class="error-row">
                <td colspan="5">
                  <div class="error-details">
                    <div v-for="(e, j) in r.errors" :key="j" class="error-item">└ {{ e }}</div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ========== 步骤 4: 完成 ========== -->
    <div v-if="step === 4" class="step-content">
      <div class="done-card" :class="{ 'has-error': totalErrors > 0 }">
        <div class="done-icon">{{ totalErrors > 0 ? '⚠️' : '✅' }}</div>
        <div class="done-text">{{ totalErrors > 0 ? '上传完成（有错误）' : '上传完成' }}</div>
      </div>

      <div class="result-card">
        <div class="section-title">结果汇总</div>
        <table class="result-table">
          <thead><tr><th>场景</th><th>上传</th><th>跳过</th><th>错误</th><th>状态</th></tr></thead>
          <tbody>
            <template v-for="(r, i) in uploadResults" :key="i">
              <tr>
                <td>{{ r.scene_name }}</td>
                <td>{{ r.uploaded }}</td>
                <td>{{ r.skipped }}</td>
                <td>{{ r.errors.length }}</td>
                <td>
                  <span v-if="r.uploaded > 0 && r.errors.length === 0" class="status-ok">✓</span>
                  <span v-else-if="r.errors.length > 0" class="status-err">✗</span>
                  <span v-else class="status-warn">-</span>
                </td>
              </tr>
              <tr v-if="r.errors.length > 0" class="error-row">
                <td colspan="5">
                  <div class="error-details">
                    <div v-for="(e, j) in r.errors" :key="j" class="error-item">└ {{ e }}</div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div class="result-summary">
          总计: 上传 {{ totalUploaded }}, 跳过 {{ totalSkipped }}, 错误 {{ totalErrors }}
        </div>
      </div>

      <div class="step-actions">
        <button class="btn-secondary" @click="goStep1">继续上传</button>
        <button class="btn-primary" @click="$router.push('/admin/images')">查看图像管理</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { apiBatchUpload } from '@/api'

const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.bmp', '.tiff'])

const step = ref(1)
const scanData = ref({ mode: 'loose', scenes: [], devices: [], warnings: [], errors: [] })
const expandedScenes = ref({})
const expandedDevices = ref(false)
const uploadResults = ref([])
const currentScene = ref('')
const currentPercent = ref(0)
const completedScenes = ref(0)

function toggleScene(index) {
  expandedScenes.value[index] = !expandedScenes.value[index]
}

function toggleDevices() {
  expandedDevices.value = !expandedDevices.value
}

const totalScenes = computed(() => scanData.value.scenes.length)
const overallPercent = computed(() => totalScenes.value ? Math.round((completedScenes.value / totalScenes.value) * 100) : 0)
const totalUploaded = computed(() => uploadResults.value.reduce((s, r) => s + r.uploaded, 0))
const totalSkipped = computed(() => uploadResults.value.reduce((s, r) => s + r.skipped, 0))
const totalErrors = computed(() => uploadResults.value.reduce((s, r) => s + r.errors.length, 0))

function onFolderSelected(e) {
  const files = Array.from(e.target.files)
  if (!files.length) return

  const scenes = {}       // sceneName -> { images: [], metas: {} }
  let rootDevicesJson = null
  const pendingReads = []  // FileReader promises

  for (const file of files) {
    const parts = file.webkitRelativePath.split('/')
    if (parts.length < 2) continue
    const fileName = parts[parts.length - 1]

    // 根目录 devices.json
    if (fileName === 'devices.json' && parts.length === 2) {
      const p = new Promise(resolve => {
        const reader = new FileReader()
        reader.onload = (ev) => {
          try {
            const data = JSON.parse(ev.target.result)
            if (Array.isArray(data)) rootDevicesJson = data
          } catch {}
          resolve()
        }
        reader.readAsText(file)
      })
      pendingReads.push(p)
      continue
    }

    // 必须在 images/ 下
    if (parts.length < 3 || parts[parts.length - 3] !== 'images') continue
    const sceneName = parts[parts.length - 2]

    if (!scenes[sceneName]) scenes[sceneName] = { images: [], metas: {} }

    const ext = '.' + fileName.split('.').pop().toLowerCase()
    const stem = fileName.replace(/\.[^.]+$/, '')

    if (ext === '.json') {
      scenes[sceneName].metas[stem] = file
    } else if (IMAGE_EXT.has(ext)) {
      scenes[sceneName].images.push({ name: fileName, stem, file })
    }
  }

  // 等待 devices.json 读取完成
  Promise.all(pendingReads).then(() => {
    // 构建场景列表
    const sceneList = []
    const allDeviceNames = new Map()  // deviceName -> Set<sceneName>
    const pattern = /^(.+?)\((.+?)\)-(.+)$/

    for (const [name, data] of Object.entries(scenes)) {
      const m = name.match(pattern)
      const category = m ? m[1] : name
      const location = m ? m[2] : ''
      const subcategory = m ? m[3] : ''

      const files = data.images.map(img => {
        if (!allDeviceNames.has(img.stem)) allDeviceNames.set(img.stem, new Set())
        allDeviceNames.get(img.stem).add(name)
        return {
          name: img.name,
          hasMeta: img.stem in data.metas,
          warning: '',
        }
      })

      // 构建 filePairs：每个图像与其 .json 元信息并排
      const filePairs = data.images.map(img => ({
        img: img.name,
        hasMeta: img.stem in data.metas,
        meta: img.stem in data.metas ? img.stem + '.json' : null,
      }))

      sceneList.push({
        name, category, location, subcategory,
        imageCount: files.length,
        metaCount: files.filter(f => f.hasMeta).length,
        filePairs,
        files,
        images: data.images,     // 保留原始 File 对象用于上传
        metas: data.metas,       // 保留原始 File 对象用于上传
      })
    }

    // 构建设备列表
    let devices = []
    const warnings = []
    const errors = []
    if (rootDevicesJson) {
      // 严格模式
      devices = rootDevicesJson
      // 检查是否有图像设备不在 devices 中
      const deviceNames = new Set(rootDevicesJson.map(d => d.设备名))
      for (const [name, scenes] of allDeviceNames) {
        if (!deviceNames.has(name)) {
          const sceneList = Array.from(scenes).join('、')
          errors.push(`图像设备 "${name}" 不在 devices.json 中（出现在场景：${sceneList}），请检查 devices.json 后重新上传`)
        }
      }
    } else {
      // 宽松模式：从文件名提取设备
      devices = Array.from(allDeviceNames.keys()).sort().map(name => ({
        设备名: name, 主控型号: '', 镜头型号: '', Sensor型号: '',
        光圈: '', 焦距: '', 分辨率: '', 帧率: '',
        白光灯珠料号: '', 红外灯珠料号: '', 壳体信息: '', 固件版本: '',
      }))
    }

    scanData.value = {
      mode: rootDevicesJson ? 'strict' : 'loose',
      scenes: sceneList,
      devices,
      warnings,
      errors,
    }
    step.value = 2
  })
}

function goStep1() {
  step.value = 1
  scanData.value = { mode: 'loose', scenes: [], devices: [], warnings: [], errors: [] }
  expandedScenes.value = {}
  expandedDevices.value = false
  uploadResults.value = []
  currentScene.value = ''
  currentPercent.value = 0
  completedScenes.value = 0
}

function goStep3() {
  step.value = 3
  uploadResults.value = scanData.value.scenes.map(s => ({
    scene_name: s.name, scene_id: 0, uploaded: 0, skipped: 0, errors: [], status: 'waiting',
  }))
  runUpload()
}

async function runUpload() {
  for (let i = 0; i < scanData.value.scenes.length; i++) {
    const scene = scanData.value.scenes[i]
    const result = uploadResults.value[i]
    currentScene.value = scene.name
    currentPercent.value = 0
    result.status = 'uploading'

    const formData = new FormData()
    formData.append('manifest', JSON.stringify({
      scene_folder_name: scene.name,
      mode: scanData.value.mode,
      default_subcategory: '',
      devices: scanData.value.devices,
    }))

    // 添加图像文件
    for (const img of scene.images) {
      formData.append('files', img.file, img.name)
    }
    // 添加同名 .json 元信息文件
    for (const img of scene.images) {
      if (img.stem in scene.metas) {
        const jsonFile = scene.metas[img.stem]
        if (jsonFile) {
          formData.append('files', jsonFile, img.stem + '.json')
        }
      }
    }

    try {
      const res = await apiBatchUpload(formData, (p) => { currentPercent.value = p })
      Object.assign(result, {
        scene_name: res.scene_name, scene_id: res.scene_id,
        uploaded: res.uploaded, skipped: res.skipped, errors: res.errors,
        status: 'done',
      })
    } catch (err) {
      result.errors = [err.message]
      result.status = 'done'
    }

    completedScenes.value = i + 1
  }
  step.value = 4
}
</script>

<style scoped>
.batch-upload { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 20px; font-weight: 700; color: #1e40af; margin-bottom: 8px; }
.page-description { font-size: 14px; color: #6b7280; margin-bottom: 20px; line-height: 1.5; }

/* 步骤条 */
.steps-bar { display: flex; align-items: center; justify-content: center; margin-bottom: 24px; padding: 16px; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.step { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; }
.step.active { background: #eff6ff; }
.step.done .step-num { background: #22c55e; color: #fff; }
.step-num { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; background: #e5e7eb; color: #6b7280; }
.step.active .step-num { background: #3b82f6; color: #fff; }
.step-label { font-size: 14px; color: #374151; }
.step-line { width: 60px; height: 2px; background: #e5e7eb; }
.step-line.active { background: #3b82f6; }

/* 选择文件夹 */
.folder-select-zone { border: 2px dashed #d1d5db; border-radius: 12px; padding: 40px; text-align: center; cursor: pointer; background: #fff; margin-top: 20px; transition: all 0.2s; }
.folder-select-zone:hover { border-color: #3b82f6; background: #eff6ff; }
.zone-icon { font-size: 48px; margin-bottom: 12px; }
.zone-text { font-size: 16px; color: #374151; font-weight: 500; }
.zone-hint { font-size: 13px; color: #9ca3af; margin-top: 8px; }

/* 使用说明 */
.help-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.help-card h3 { font-size: 15px; font-weight: 600; color: #374151; margin-bottom: 12px; }
.help-structure { font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; color: #4b5563; background: #f8fafc; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; white-space: pre; }
.help-rules p { font-size: 13px; color: #6b7280; margin: 4px 0; }

/* 扫描结果 */
.scan-result { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.mode-badge { padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; }
.mode-badge.strict { background: #fef3c7; color: #92400e; }
.mode-badge.loose { background: #dbeafe; color: #1e40af; }
.mode-desc { font-size: 13px; color: #6b7280; }
.section-title { font-size: 14px; font-weight: 600; color: #374151; padding: 8px 0; border-bottom: 1px solid #e5e7eb; margin-bottom: 8px; }

/* 场景列表 */
.scene-list { margin-bottom: 16px; }
.scene-item { background: #f8fafc; border-radius: 8px; margin-bottom: 8px; overflow: hidden; }
.scene-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; cursor: pointer; user-select: none; }
.scene-header:hover { background: #eff6ff; }
.scene-toggle { font-size: 12px; color: #6b7280; width: 16px; flex-shrink: 0; }
.scene-name { font-weight: 600; color: #1e40af; }
.scene-stats { font-size: 13px; color: #6b7280; margin-left: auto; white-space: nowrap; }

/* 文件列表 - 并排显示 */
.file-list { padding: 0 12px 12px 36px; }
.file-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; padding: 3px 0; border-bottom: 1px solid #f3f4f6; }
.file-row.header-row { font-weight: 600; color: #6b7280; font-size: 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; margin-bottom: 4px; }
.file-col-img { color: #374151; }
.file-col-meta { color: #6b7280; }
.file-col-meta.no-meta { color: #d1d5db; }

/* 设备列表 */
.device-section { margin-bottom: 16px; }
.device-title { cursor: pointer; user-select: none; }
.device-title:hover { color: #1e40af; }
.device-table { }
.device-row { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #f3f4f6; }
.device-row.header { background: #f8fafc; font-weight: 600; color: #374151; }

/* 警告 */
.warnings { background: #fef3c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }
.warning-item { font-size: 13px; color: #92400e; margin: 4px 0; }

/* 错误（阻塞上传） */
.errors { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }
.errors-title { font-weight: 600; color: #dc2626; margin-bottom: 8px; font-size: 14px; }
.errors .error-msg { font-size: 13px; color: #dc2626; margin: 4px 0; padding-left: 12px; }

/* 按钮 */
.step-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 16px; }
.btn-primary, .btn-secondary { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
.btn-primary { background: #3b82f6; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #9ca3af; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-secondary:hover { background: #f9fafb; }

/* 上传进度 */
.progress-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 16px; }
.progress-bar-wrap { margin-bottom: 12px; }
.progress-bar { height: 24px; background: #e5e7eb; border-radius: 12px; overflow: hidden; margin-bottom: 4px; }
.progress-bar.small { height: 8px; margin-top: 4px; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 12px; transition: width 0.3s; }
.progress-label { font-size: 13px; color: #6b7280; text-align: center; }
.current-scene { font-size: 13px; color: #374151; }

/* 结果 */
.result-card, .done-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 16px; }
.done-card { text-align: center; padding: 32px; }
.done-card.has-error { border-left: 4px solid #f59e0b; }
.done-icon { font-size: 48px; margin-bottom: 8px; }
.done-text { font-size: 18px; font-weight: 600; color: #374151; }
.result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.result-table th, .result-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f3f4f6; }
.result-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.status-ok { color: #22c55e; font-weight: 600; }
.status-err { color: #ef4444; font-weight: 600; }
.status-ing { color: #f59e0b; }
.status-wait { color: #9ca3af; }
.status-warn { color: #9ca3af; }
.error-row td { padding: 0; }
.error-details { padding: 8px 12px; background: #fef2f2; border-radius: 0 0 6px 6px; }
.error-item { font-size: 12px; color: #dc2626; padding: 2px 0; }
.result-summary { font-size: 14px; font-weight: 600; color: #374151; padding-top: 12px; border-top: 1px solid #e5e7eb; margin-top: 12px; }

@media (max-width: 768px) {
  .device-row { grid-template-columns: 1fr; }
  .device-row.header { display: none; }
  .file-row { grid-template-columns: 1fr; }
}
</style>
