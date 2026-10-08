<template>
  <section ref="root" class="activity-timeline" aria-label="个人操作时间线">
    <div class="page-head">
      <div>
        <span class="eyebrow">MY FOOTPRINTS / 圈子足迹</span>
        <h1>我的痕迹线<span class="heading-dot">.</span></h1>
        <p>{{ total }} 次圈子操作</p>
      </div>
      <select v-model="year" class="field-select" aria-label="筛选操作年份">
        <option value="">全部年份</option>
        <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
      </select>
    </div>
    <div class="activity-filters">
      <select
        v-model="circle"
        class="field-select"
        aria-label="筛选操作所属圈子"
      >
        <option value="">全部圈子</option>
        <option v-for="c in circles" :key="c.id" :value="c.id">
          {{ c.name }}
        </option>
      </select>
      <select v-model="kind" class="field-select" aria-label="筛选操作类型">
        <option value="">全部操作</option>
        <option v-for="(label, key) in kinds" :key="key" :value="key">
          {{ label }}
        </option>
      </select>
    </div>
    <div v-if="loading" class="activity-skeleton" aria-label="正在加载操作记录">
      <div v-for="i in 5" :key="i" class="skeleton" />
    </div>
    <template v-else>
      <section
        v-for="chapter in chapters"
        :key="chapter.key"
        class="activity-chapter"
      >
        <header>
          <span>{{ chapter.key.slice(5) }}</span>
          <h2>
            {{ chapter.key.slice(0, 4) }} 年<small>{{ chapter.name }}</small>
          </h2>
        </header>
        <ol class="activity-events">
          <li
            v-for="item in chapter.items"
            :key="item.id"
            :data-action="item.action"
          >
            <time :datetime="item.created_at"
              ><strong>{{ day(item.created_at) }}</strong
              ><span>{{ clock(item.created_at) }}</span></time
            >
            <span
              class="activity-symbol"
              :class="{
                destructive:
                  item.action.endsWith('_delete') ||
                  item.action === 'circle_leave',
              }"
              ><component :is="icons[item.target_kind]" :size="18"
            /></span>
            <div class="activity-event-copy">
              <h3>{{ item.action_label }}</h3>
              <p>{{ item.target_label }}</p>
              <span class="activity-circle"
                ><UsersRound :size="13" />{{ item.circle_name }}</span
              >
            </div>
            <button
              v-if="item.can_open_post"
              class="icon-button"
              title="查看关联记录"
              aria-label="查看关联记录"
              @click="$emit('open-post', { id: item.post_id })"
            >
              <ArrowUpRight :size="18" />
            </button>
          </li>
        </ol>
      </section>
      <div v-if="error" class="empty-state" role="alert">
        <p>{{ error }}</p>
        <button class="outline" @click="load(failedMore)">重试</button>
      </div>
      <div v-else-if="!items.length" class="empty-state">
        {{
          circle || year || kind
            ? '没有符合筛选条件的操作记录。'
            : '还没有圈子操作记录。'
        }}
      </div>
      <div v-else class="activity-end">
        <button
          v-if="items.length < total"
          class="outline"
          :disabled="loadingMore"
          @click="load(true)"
        >
          {{ loadingMore ? '加载中…' : '更早的足迹' }}<ChevronDown :size="16" />
        </button>
        <span v-else>已到最早的足迹</span>
      </div>
    </template>
  </section>
</template>

<script setup>
import {
  computed,
  inject,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  ref,
  watch,
} from 'vue'
import {
  ArrowUpRight,
  ChevronDown,
  Flag,
  GitBranch,
  Images,
  MessageCircle,
  NotebookPen,
  UsersRound,
} from 'lucide-vue-next'
import api from '../api'

defineEmits(['open-post'])
const revision = inject('revision')
const root = ref(null)
const items = ref([]),
  circles = ref([]),
  years = ref([]),
  total = ref(0)
const circle = ref(''),
  year = ref(''),
  kind = ref('')
const loading = ref(true),
  loadingMore = ref(false),
  error = ref(''),
  failedMore = ref(false)
const kinds = {
  circle: '圈子',
  post: '记录',
  album: '分册',
  line: '时间线',
  comment: '评论',
  report: '举报',
}
const icons = {
  circle: UsersRound,
  post: NotebookPen,
  album: Images,
  line: GitBranch,
  comment: MessageCircle,
  report: Flag,
}
const chapters = computed(() => {
  const groups = new Map()
  for (const item of items.value) {
    const key = item.created_at.slice(0, 7)
    if (!groups.has(key))
      groups.set(key, { key, name: `${Number(key.slice(5))} 月`, items: [] })
    groups.get(key).items.push(item)
  }
  return [...groups.values()]
})
const day = (value) => `${Number(value.slice(8, 10))} 日`
const clock = (value) => value.slice(11, 16)
let sequence = 0,
  active = false
async function load(more = false, refresh = false) {
  if (typeof more !== 'boolean') more = false
  if (more && loadingMore.value) return
  const request = ++sequence
  loading.value = !more && !refresh
  loadingMore.value = more
  error.value = ''
  failedMore.value = more
  const keepCount = refresh ? items.value.length : 0
  if (!more && !refresh) items.value = []
  try {
    const params = {
      circle_id: circle.value || undefined,
      year: year.value || undefined,
      kind: kind.value || undefined,
      limit: 50,
    }
    const { data } = await api.get('/api/me/timeline', {
      params: {
        ...params,
        before_id: more ? items.value.at(-1)?.id : undefined,
      },
    })
    while (
      request === sequence &&
      data.items.length < keepCount &&
      data.items.length < data.total
    ) {
      const page = await api.get('/api/me/timeline', {
        params: {
          ...params,
          before_id: data.items.at(-1)?.id,
        },
      })
      if (!page.data.items.length) break
      data.items.push(...page.data.items)
    }
    if (request !== sequence) return
    items.value = more ? [...items.value, ...data.items] : data.items
    total.value = data.total
    circles.value = data.circles
    years.value = data.years
  } catch (e) {
    if (request === sequence) error.value = e.userMessage || '加载操作记录失败'
  } finally {
    if (request === sequence) loading.value = loadingMore.value = false
  }
}
onActivated(() => {
  active = true
  load(false, !!items.value.length)
})
onDeactivated(() => {
  active = false
})
onBeforeUnmount(() => {
  sequence++
})
watch([circle, year, kind], async () => {
  load()
  await nextTick()
  root.value?.closest('.body-grid')?.scrollTo({ top: 0, behavior: 'instant' })
})
watch(revision, () => {
  if (active) load(false, !!items.value.length)
})
</script>
