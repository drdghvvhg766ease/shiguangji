<template>
  <section class="export-card" aria-label="数据备份">
    <header class="export-head">
      <div>
        <h2>数据备份</h2>
        <p>把这个圈子的记录打包成 ZIP：原始照片、视频、语音，加上一份可读的清单。</p>
      </div>
      <Package class="export-badge" :size="22" />
    </header>

    <div class="export-range">
      <label>
        <span>从</span>
        <input v-model="dateFrom" type="date" :max="dateTo || undefined" />
      </label>
      <label>
        <span>到</span>
        <input v-model="dateTo" type="date" :min="dateFrom || undefined" />
      </label>
      <button
        class="primary export-start"
        type="button"
        :disabled="busy || running"
        @click="startExport"
      >
        <Loader2 v-if="running" class="export-spin" :size="15" />
        <Download v-else :size="15" />
        {{ running ? '正在打包…' : '生成导出包' }}
      </button>
    </div>
    <p class="export-tip">
      留空即导出全部记录；文件较大时可先按年份分段导出，导出包在 {{ expireHours }} 小时后自动清理。
    </p>

    <p v-if="error" class="export-error" role="alert">{{ error }}</p>

    <div v-if="current" class="export-current" :class="current.status">
      <div class="export-current-main">
        <strong>
          <template v-if="current.status === 'ready'">导出包已就绪</template>
          <template v-else-if="current.status === 'failed'">打包失败</template>
          <template v-else>正在整理 {{ rangeLabel }}</template>
        </strong>
        <small v-if="current.status === 'ready'">
          {{ current.post_count }} 条记录 · {{ current.media_count }} 个文件 ·
          {{ humanSize(current.file_size) }} · {{ expireLabel(current.expires_at) }}
        </small>
        <small v-else-if="current.status === 'failed'">{{ current.message || '请稍后重试' }}</small>
        <small v-else>打包完成后可在这里下载，期间可以先去别处看看。</small>
      </div>
      <a
        v-if="current.status === 'ready'"
        class="outline export-download"
        :href="current.download_url"
        download
      >
        <Download :size="14" />下载 ZIP
      </a>
      <button
        v-else-if="current.status === 'failed'"
        class="outline"
        type="button"
        @click="startExport"
      >
        重试
      </button>
    </div>

    <div v-if="history.length" class="export-history">
      <h3>最近导出</h3>
      <ul>
        <li v-for="job in history" :key="job.id">
          <span class="export-when">{{ shortTime(job.finished_at || job.created_at) }}</span>
          <span class="export-scope">{{ jobRange(job) }}</span>
          <span class="export-size">{{ job.status === 'ready' ? humanSize(job.file_size) : '—' }}</span>
          <a v-if="job.status === 'ready'" :href="job.download_url" download>下载</a>
          <em v-else>{{ job.status === 'failed' ? '失败' : '处理中' }}</em>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Download, Loader2, Package } from 'lucide-vue-next'
import api from '../api'

const props = defineProps({
  circleId: { type: Number, required: true },
  expireHours: { type: Number, default: 72 },
})

const dateFrom = ref('')
const dateTo = ref('')
const job = ref(null)
const history = ref([])
const busy = ref(false)
const error = ref('')
const running = computed(() => job.value && ['pending', 'running'].includes(job.value.status))
const current = computed(() => job.value)
let timer = null

const rangeLabel = computed(() => {
  const from = job.value?.date_from || '最早'
  const to = job.value?.date_to || '至今'
  return `${from} ～ ${to}`
})

function humanSize(bytes) {
  const value = Number(bytes || 0)
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let index = 0
  let size = value
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${index === 0 ? Math.round(size) : size.toFixed(1)} ${units[index]}`
}

function shortTime(value) {
  return value ? String(value).slice(5, 16).replace('T', ' ') : '—'
}

function jobRange(item) {
  if (!item.date_from && !item.date_to) return '全部记录'
  return `${item.date_from || '最早'} ~ ${item.date_to || '至今'}`
}

function expireLabel(value) {
  if (!value) return ''
  const left = new Date(value).getTime() - Date.now()
  if (left <= 0) return '已过期'
  const hours = Math.floor(left / 3600000)
  return hours >= 1 ? `${hours} 小时后过期` : '即将过期'
}

function stopPolling() {
  clearInterval(timer)
  timer = null
}

function poll(id) {
  stopPolling()
  timer = setInterval(async () => {
    try {
      const { data } = await api.get(`/api/exports/${id}`)
      job.value = data
      if (!['pending', 'running'].includes(data.status)) {
        stopPolling()
        await loadHistory()
      }
    } catch {
      stopPolling()
      error.value = '查询导出状态失败，请稍后重试'
    }
  }, 2000)
}

async function startExport() {
  if (busy.value || running.value) return
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/api/circles/${props.circleId}/exports`, {
      date_from: dateFrom.value || null,
      date_to: dateTo.value || null,
    })
    job.value = data
    if (['pending', 'running'].includes(data.status)) poll(data.id)
    else await loadHistory()
  } catch (e) {
    error.value = e.userMessage || '创建导出任务失败'
  } finally {
    busy.value = false
  }
}

async function loadHistory() {
  try {
    const { data } = await api.get(`/api/circles/${props.circleId}/exports`)
    history.value = Array.isArray(data) ? data.slice(0, 4) : []
    const latest = history.value[0]
    if (!job.value && latest) job.value = latest
  } catch {
    history.value = []
  }
}

onMounted(loadHistory)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.export-card {
  margin-top: 22px;
  padding: 18px 20px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
}
.export-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.export-head h2 {
  margin: 0 0 3px;
  font-family: var(--serif);
  font-size: 17px;
  color: var(--ink);
}
.export-head p {
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--muted);
}
.export-badge {
  margin-left: auto;
  flex: none;
  color: var(--gold);
}
.export-range {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}
.export-range label {
  display: grid;
  gap: 3px;
  font-size: 10px;
  color: var(--muted);
}
.export-range input {
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--paper);
  color: var(--ink);
  font-size: 12px;
  font-family: inherit;
  color-scheme: light dark;
}
.export-start {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  font-size: 12px;
}
.export-tip {
  margin: 9px 0 0;
  font-size: 10px;
  line-height: 1.6;
  color: var(--muted);
}
.export-error {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--terracotta-dark);
}
.export-current {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 11px 13px;
  border: 1px dashed var(--line);
  border-radius: 9px;
  background: color-mix(in srgb, var(--paper) 64%, var(--surface));
}
.export-current.ready {
  border-style: solid;
  border-color: color-mix(in srgb, var(--pine) 34%, var(--line));
  background: color-mix(in srgb, var(--sage) 12%, var(--surface));
}
.export-current.failed {
  border-color: color-mix(in srgb, var(--terracotta) 40%, var(--line));
}
.export-current-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.export-current-main strong {
  font-size: 12px;
  color: var(--ink);
}
.export-current-main small {
  font-size: 10px;
  color: var(--muted);
}
.export-download {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  font-size: 11px;
  text-decoration: none;
  white-space: nowrap;
}
.export-spin {
  animation: export-spin 1s linear infinite;
}
@keyframes export-spin {
  to {
    transform: rotate(360deg);
  }
}
.export-history {
  margin-top: 14px;
}
.export-history h3 {
  margin: 0 0 6px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.export-history ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.export-history li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 9px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--ink) 4%, transparent);
  font-size: 11px;
  color: var(--muted);
}
.export-when {
  font-variant-numeric: tabular-nums;
}
.export-scope {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.export-size {
  color: var(--ink);
}
.export-history a {
  color: var(--terracotta-dark);
  text-decoration: none;
}
.export-history em {
  font-style: normal;
  opacity: 0.7;
}
@media (max-width: 650px) {
  .export-card {
    padding: 15px 14px 13px;
  }
  .export-range {
    gap: 8px;
  }
  .export-range label {
    flex: 1;
  }
  .export-range input {
    width: 100%;
  }
  .export-start {
    width: 100%;
    justify-content: center;
  }
  .export-current {
    flex-direction: column;
    align-items: stretch;
    gap: 9px;
  }
  .export-download {
    justify-content: center;
  }
}
</style>
