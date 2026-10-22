<template>
  <section aria-label="玩法" class="play-page">
    <div class="page-head">
      <div>
        <span class="eyebrow">PLAY TOGETHER / 一起玩</span>
        <h1>一起玩<span class="heading-dot">.</span></h1>
        <p>拆一段旧时光，一起完成任务，再翻翻这一年的成绩单</p>
      </div>
    </div>
    <nav class="segmented play-tabs" aria-label="玩法分类">
      <button
        v-for="t in tabs"
        :key="t.key"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        <component :is="t.icon" :size="15" />{{ t.label }}
      </button>
    </nav>

    <!-- 回忆盲盒 -->
    <template v-if="tab === 'box'">
      <article class="memory-box" :class="{ opened: boxPost }">
        <div v-if="boxLoading" class="skeleton box-skeleton" />
        <template v-else-if="boxPost">
          <div class="box-reason">
            <span class="box-badge">{{ boxReason }}</span>
            <span v-if="boxYears" class="box-years">距今 {{ boxYears }} 年</span>
          </div>
          <div class="box-body">
            <button
              v-if="boxCover"
              class="box-cover"
              type="button"
              :aria-label="`打开回忆：${boxPost.content}`"
              @click="openBoxPost"
            >
              <img :src="boxCover" :alt="boxPost.content" decoding="async" />
            </button>
            <div class="box-copy">
              <p class="box-text">
                {{ boxPost.content || '这一刻，没有文字。' }}
              </p>
              <p class="box-meta">
                {{ boxPost.event_date }} ·
                {{ boxPost.nickname || boxPost.username }}
                <span v-if="boxPost.location_name"
                  >· {{ boxPost.location_name }}</span
                >
              </p>
              <div class="box-actions">
                <button class="primary" type="button" @click="openBoxPost">
                  <ArrowUpRight :size="16" />打开这段回忆
                </button>
                <button class="outline" type="button" @click="drawBox">
                  <Gift :size="16" />再拆一个
                </button>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="box-empty">
          <span class="box-seal">盲</span>
          <h2>今天的回忆盲盒</h2>
          <p>优先翻出往年今日，没有就从旧时光里抽一段。</p>
          <button class="primary" type="button" @click="drawBox">
            <Gift :size="18" />拆盲盒
          </button>
        </div>
      </article>
    </template>

    <!-- 共同任务 -->
    <template v-else-if="tab === 'quest'">
      <div class="section-head">
        <h2>进行中的共同任务</h2>
        <button class="outline" type="button" @click="questFormOpen = !questFormOpen">
          <Plus :size="16" />发起任务
        </button>
      </div>
      <form v-if="questFormOpen" class="quest-form" @submit.prevent="createQuest">
        <div class="form-split">
          <label class="field"
            >任务名称<input
              v-model="questForm.title"
              maxlength="80"
              required
              placeholder="例如：本月一起拍 10 张天空" /></label
          ><label class="field"
            >目标次数<input
              type="number"
              min="1"
              max="99"
              v-model.number="questForm.target_count" /></label
          >
        </div>
        <div class="form-split">
          <label class="field"
            >开始日期<input type="date" v-model="questForm.start_date" required /></label
          ><label class="field"
            >结束日期<input type="date" v-model="questForm.end_date" required /></label
          >
        </div>
        <label class="field"
          >一句话说明<input
            v-model="questForm.description"
            maxlength="200"
            placeholder="想让大家怎么一起完成"
        /></label>
        <div class="form-actions">
          <button class="outline" type="button" @click="questFormOpen = false">
            取消
          </button>
          <button class="primary" :disabled="questBusy">
            {{ questBusy ? '创建中…' : '创建任务' }}
          </button>
        </div>
      </form>
      <p v-if="questError" class="form-error">{{ questError }}</p>
      <div v-if="!quests.length" class="empty-state">
        还没有共同任务，发起第一个吧。
      </div>
      <article v-for="q in quests" :key="q.id" class="quest-card">
        <header>
          <div>
            <strong>{{ q.title }}</strong>
            <small
              >{{ q.start_date }} → {{ q.end_date }} · {{ q.creator }} 发起</small
            >
          </div>
          <span class="quest-status" :class="{ done: q.done, active: q.active && !q.done }">
            {{ q.done ? '已达成' : q.active ? '进行中' : '已结束' }}
          </span>
        </header>
        <p v-if="q.description" class="quest-desc">{{ q.description }}</p>
        <div class="quest-progress">
          <div class="quest-bar">
            <span
              :style="{
                width: `${Math.min(100, (q.total / q.target_count) * 100)}%`,
              }"
            />
          </div>
          <small
            >{{ q.total }} / {{ q.target_count }} 次 · {{ q.participants }}
            人参与 · 我 {{ q.mine }} 次</small
          >
        </div>
        <ul v-if="q.recent.length" class="quest-log">
          <li v-for="c in q.recent" :key="c.id">
            <span>{{ c.name }}</span>
            <em>{{ c.note || '打卡' }}</em>
          </li>
        </ul>
        <div class="quest-actions">
          <input
            v-model="checkinDraft[q.id]"
            class="quest-note"
            maxlength="80"
            placeholder="打卡留言（可选）"
            :aria-label="`${q.title} 打卡留言`"
          />
          <button
            class="secondary"
            type="button"
            :disabled="!q.active || questBusy"
            @click="checkin(q)"
          >
            <Check :size="16" />打卡
          </button>
          <button
            v-if="canManageQuest(q)"
            class="text-button danger-text"
            type="button"
            @click="removeQuest(q)"
          >
            删除
          </button>
        </div>
      </article>
    </template>

    <!-- 年度回顾 -->
    <template v-else>
      <div class="recap-toolbar">
        <div class="year-pills" role="group" aria-label="选择回顾年份">
          <button
            v-for="y in years"
            :key="y"
            type="button"
            :class="{ active: recapYear === y }"
            @click="loadRecap(y)"
          >
            {{ y }}
          </button>
        </div>
        <button class="outline" type="button" @click="loadRecap(recapYear, recapMonth === 12 ? null : (recapMonth || 0) + 1)">
          换一个月
        </button>
      </div>
      <div v-if="recapLoading" class="skeleton recap-skeleton" />
      <p v-else-if="recapError" class="empty-state">{{ recapError }}</p>
      <article v-else-if="recap" class="recap-card">
        <header class="recap-head">
          <span class="recap-en">RECAP</span>
          <h2>{{ recap.label }}</h2>
          <p>{{ recap.summary }}</p>
        </header>
        <dl class="recap-stats">
          <div>
            <dt>记录</dt>
            <dd>{{ recap.posts }}</dd>
          </div>
          <div>
            <dt>影像</dt>
            <dd>{{ recap.media }}</dd>
          </div>
          <div>
            <dt>地方</dt>
            <dd>{{ recap.places.length }}</dd>
          </div>
          <div>
            <dt>最长连续</dt>
            <dd>{{ recap.longest_streak }}<small>天</small></dd>
          </div>
        </dl>
        <div class="recap-blocks">
          <section>
            <h3>最常出现的人</h3>
            <ul class="recap-people">
              <li v-for="p in recap.people" :key="p.user_id">
                <span class="avatar av-teal">{{ p.name.slice(0, 1) }}</span>
                <span>{{ p.name }}</span>
                <small>{{ p.count }} 条</small>
              </li>
            </ul>
          </section>
          <section>
            <h3>关键词</h3>
            <ul class="recap-tags">
              <li v-for="t in recap.tags" :key="t.tag">
                {{ t.tag }}<small>{{ t.count }}</small>
              </li>
            </ul>
          </section>
          <section>
            <h3>去过的地方</h3>
            <p class="recap-places">
              {{ recap.places.join('、') || '这一年还没留下地点' }}
            </p>
          </section>
        </div>
        <footer class="recap-hottest">
          <div v-if="recap.hottest.cover" class="recap-thumb">
            <img :src="recap.hottest.cover" alt="" decoding="async" />
          </div>
          <div>
            <small>被赞最多的一条</small>
            <p>{{ recap.hottest.content }}</p>
            <span>{{ recap.hottest.likes }} 次赞</span>
          </div>
          <button class="outline" type="button" @click="openRecapPost">
            打开
          </button>
        </footer>
      </article>
    </template>
  </section>
</template>

<script setup>
import { computed, inject, onActivated, reactive, ref, watch } from 'vue'
import {
  ArrowUpRight,
  Check,
  Gift,
  ListChecks,
  Plus,
  Sparkles,
  Trophy,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { confirmDialog } from '../utils/confirm'

const emit = defineEmits(['open-post'])
const auth = useAuthStore()
const toast = inject('toast')
const revision = inject('revision')

const tabs = [
  { key: 'box', label: '回忆盲盒', icon: Gift },
  { key: 'quest', label: '共同任务', icon: ListChecks },
  { key: 'recap', label: '年度回顾', icon: Trophy },
]
const tab = ref('box')

/* ---- 盲盒 ---- */
const boxPost = ref(null)
const boxReason = ref('')
const boxYears = ref(0)
const boxLoading = ref(false)
const boxCover = computed(() => {
  const photo = boxPost.value?.media?.find((m) => m.kind === 'photo')
  return photo?.preview_url || photo?.original_url || ''
})
async function drawBox() {
  const circle = auth.currentCircleId
  if (!circle) return
  boxLoading.value = true
  try {
    const { data } = await api.get(`/api/circles/${circle}/memory-box`)
    if (circle !== auth.currentCircleId) return
    boxPost.value = data.post
    boxReason.value = data.reason || '随机回忆'
    boxYears.value = data.years_ago || 0
    if (!data.post) toast('圈子里还没有记录，先发一条吧')
  } catch (e) {
    toast(e.userMessage || '盲盒打不开，请稍后重试')
  } finally {
    boxLoading.value = false
  }
}
function openBoxPost() {
  if (!boxPost.value) return
  emit('open-post', {
    id: boxPost.value.id,
    mediaId: boxPost.value.media?.[0]?.id,
  })
}

/* ---- 共同任务 ---- */
const quests = ref([])
const questFormOpen = ref(false)
const questBusy = ref(false)
const questError = ref('')
const checkinDraft = reactive({})
const today = new Date()
const iso = (d) => new Intl.DateTimeFormat('sv-SE').format(d)
const plusDays = (n) => {
  const d = new Date(today)
  d.setDate(d.getDate() + n)
  return iso(d)
}
const questForm = reactive({
  title: '',
  description: '',
  tag: '',
  target_count: 5,
  start_date: iso(today),
  end_date: plusDays(30),
})
function canManageQuest(q) {
  return q.created_by === auth.user?.id || auth.canManage
}
async function loadQuests() {
  const circle = auth.currentCircleId
  if (!circle) {
    quests.value = []
    return
  }
  try {
    const { data } = await api.get(`/api/circles/${circle}/challenges`)
    if (circle !== auth.currentCircleId) return
    quests.value = data
  } catch (e) {
    questError.value = e.userMessage || '任务加载失败'
  }
}
async function createQuest() {
  const circle = auth.currentCircleId
  if (!circle || questBusy.value) return
  questBusy.value = true
  questError.value = ''
  try {
    const { data } = await api.post(`/api/circles/${circle}/challenges`, {
      ...questForm,
      title: questForm.title.trim(),
    })
    quests.value = [data, ...quests.value]
    questFormOpen.value = false
    questForm.title = ''
    questForm.description = ''
    toast('共同任务已发起')
  } catch (e) {
    questError.value = e.userMessage || '创建任务失败'
  } finally {
    questBusy.value = false
  }
}
async function checkin(q) {
  const circle = auth.currentCircleId
  if (!circle || questBusy.value) return
  questBusy.value = true
  try {
    const { data } = await api.post(
      `/api/circles/${circle}/challenges/${q.id}/checkins`,
      { note: (checkinDraft[q.id] || '').trim() },
    )
    const at = quests.value.findIndex((x) => x.id === q.id)
    if (at >= 0) quests.value[at] = data
    checkinDraft[q.id] = ''
    toast(data.done ? '任务达成，真棒' : '打卡完成')
  } catch (e) {
    questError.value = e.userMessage || '打卡失败'
  } finally {
    questBusy.value = false
  }
}
async function removeQuest(q) {
  if (
    !(await confirmDialog({
      title: '删除共同任务',
      message: `「${q.title}」的打卡记录会一起删除。`,
      confirmText: '删除',
      danger: true,
    }))
  )
    return
  try {
    await api.delete(`/api/circles/${auth.currentCircleId}/challenges/${q.id}`)
    quests.value = quests.value.filter((x) => x.id !== q.id)
    toast('任务已删除')
  } catch (e) {
    questError.value = e.userMessage || '删除失败'
  }
}

/* ---- 年度回顾 ---- */
const years = ref([])
const recap = ref(null)
const recapYear = ref(null)
const recapMonth = ref(null)
const recapLoading = ref(false)
const recapError = ref('')
async function loadYears() {
  const circle = auth.currentCircleId
  if (!circle) return
  try {
    const { data } = await api.get(`/api/circles/${circle}/timeline`)
    if (circle !== auth.currentCircleId) return
    years.value = [...new Set(data.map((m) => m.year))].sort((a, b) => b - a)
    if (!recapYear.value && years.value.length) loadRecap(years.value[0])
  } catch {
    /* 时间线不可用时仍可手动触发回顾 */
  }
}
async function loadRecap(year, month = null) {
  const circle = auth.currentCircleId
  if (!circle) return
  recapLoading.value = true
  recapError.value = ''
  recapYear.value = year || recapYear.value
  recapMonth.value = month
  try {
    const params = {}
    if (recapYear.value) params.year = recapYear.value
    if (month) params.month = month
    const { data } = await api.get(`/api/circles/${circle}/recap`, { params })
    if (circle !== auth.currentCircleId) return
    recap.value = data
    recapYear.value = data.year
    recapMonth.value = data.month
  } catch (e) {
    recap.value = null
    recapError.value = e.userMessage || '这段时间还没有记录'
  } finally {
    recapLoading.value = false
  }
}
function openRecapPost() {
  if (!recap.value?.hottest?.post_id) return
  emit('open-post', { id: recap.value.hottest.post_id })
}

let loadedRevision = -1
onActivated(() => {
  if (loadedRevision !== revision.value) {
    loadQuests()
    loadYears()
    loadedRevision = revision.value
  }
})
watch(tab, (key) => {
  if (key === 'quest' && !quests.value.length) loadQuests()
  if (key === 'recap' && !years.value.length) loadYears()
})
watch(
  () => auth.currentCircleId,
  () => {
    boxPost.value = null
    quests.value = []
    years.value = []
    recap.value = null
    recapYear.value = null
    recapMonth.value = null
    loadQuests()
    loadYears()
  },
)
</script>
