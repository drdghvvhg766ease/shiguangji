<template>
  <section
    ref="root"
    aria-label="生活痕迹线"
    class="chronicle"
    :style="{ '--chronicle-nav-height': `${navigationHeight}px` }"
  >
    <div class="page-head">
      <div>
        <span class="eyebrow">OUR DAYS / 生活影集</span>
        <h1>生活痕迹线<span class="heading-dot">.</span></h1>
        <p>
          {{ total }} 条记录 ·
          {{ auth.currentCircle?.name || '圈子生活' }}
        </p>
      </div>
      <select v-model="year" class="field-select" aria-label="选择年份">
        <option value="all">全部年份</option>
        <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
      </select>
    </div>
    <div class="line-toolbar">
      <div class="segmented">
        <button
          :class="{ active: mode === 'stories' }"
          @click="mode = 'stories'"
        >
          影集时间线</button
        ><button :class="{ active: mode === 'map' }" @click="mode = 'map'">
          <MapPin :size="15" />足迹地图
        </button>
      </div>
      <div>
        <button
          v-if="canManage"
          class="icon-button"
          title="编辑时间线"
          aria-label="编辑时间线"
          @click="editLine"
        >
          <Pencil :size="17" /></button
        ><button
          v-if="canManage"
          class="icon-button"
          title="删除时间线"
          aria-label="删除时间线"
          @click="removeLine"
        >
          <Trash2 :size="17" /></button
        ><button
          class="text-button"
          :disabled="!auth.currentCircleId"
          @click="newLine"
        >
          <Plus :size="17" />新建时间线
        </button>
      </div>
    </div>
    <nav class="line-tree" aria-label="主线与分支">
      <button
        :class="{ active: selectedLine === null }"
        @click="selectedLine = null"
      >
        汇总主线<small>{{ allCount }}</small></button
      ><button
        v-for="line in orderedLines"
        :key="line.id"
        :class="{ active: selectedLine === line.id }"
        @click="selectedLine = line.id"
      >
        <GitBranch :size="15" />{{ line.depth ? '↳ ' : '' }}{{ line.title
        }}<small>{{ line.album_count }} 本分册</small>
      </button>
    </nav>
    <p v-if="currentLine" class="line-description">
      {{ parentLabel }} / {{ currentLine.title }} ·
      {{ kindLabels[currentLine.kind] }}
    </p>
    <FootprintMap
      v-if="mode === 'map' && !loading && !error"
      :posts="mapPosts"
      @open-post="$emit('open-post', $event)"
    />
    <div
      v-if="mode === 'stories' && filtered.length && !error && !loading"
      ref="navigation"
      class="chronicle-navigation"
    >
      <nav class="month-nav" aria-label="月份导航">
        <button
          v-for="m in filtered"
          :key="key(m)"
          :class="{ active: activeMonth === key(m) }"
          @click="jump(m)"
        >
          {{ m.year }} / {{ String(m.month).padStart(2, '0')
          }}<small>{{ m.post_count }}</small>
        </button>
      </nav>
      <MemoryNavigator
        :posts="mapPosts"
        :active-id="activePostId"
        @navigate="goToPost"
        @open="openCurrent"
      />
    </div>
    <div v-if="loading" class="feed-skeleton" aria-label="正在加载">
      <div v-for="i in 3" :key="i" class="skeleton" />
    </div>
    <div v-else-if="error" class="empty-state" role="alert">
      <p>{{ error }}</p>
      <button class="outline" @click="load">重试</button>
    </div>
    <template v-else-if="mode === 'stories'"
      ><section
        v-for="m in filtered"
        :key="key(m)"
        :data-month="key(m)"
        class="month-chapter"
      >
        <header class="chapter-heading">
          <div>
            <span class="chapter-number">{{
              String(m.month).padStart(2, '0')
            }}</span>
            <h2>
              {{ m.year
              }}<small
                >{{ monthNames[m.month - 1] }} ·
                {{ m.post_count }} 条记录</small
              >
            </h2>
          </div>
          <span class="chapter-line"></span>
        </header>
        <div v-for="d in m.days" :key="d.event_date" class="chronicle-day">
          <div class="chronicle-date">
            <strong>{{ Number(d.event_date.slice(8)) }}</strong
            ><span>{{ weekday(d.event_date) }}</span
            ><small>{{ d.posts.length }} 条记录</small>
          </div>
          <div class="day-stories">
            <article
              v-for="p in d.posts"
              :key="p.id"
              :data-story="p.id"
              :data-current="p.id === activePostId"
              class="chronicle-story"
              :class="{
                'chapter-feature': p.id === featured(m),
                'text-only': !p.media.length,
              }"
            >
              <div
                v-if="p.media.length"
                class="chronicle-images"
                :class="{
                  multiple: p.media.length > 1,
                  three: p.media.length > 2,
                }"
              >
                <button
                  v-for="(media, i) in p.media.slice(0, 3)"
                  :key="media.id"
                  :aria-label="`查看 ${p.nickname || p.username} 的第 ${i + 1} 个影像`"
                  @click="open(p, media, $event)"
                >
                  <MediaPreview :media="media" :alt="p.content" /><span
                    v-if="i === 2 && p.media.length > 3"
                    class="extra-photos"
                    >+{{ p.media.length - 3 }}</span
                  >
                </button>
              </div>
              <div class="chronicle-copy">
                <div class="story-byline">
                  <span
                    ><span class="author-dot"></span
                    >{{ p.nickname || p.username }}</span
                  ><span
                    >{{ p.activity_tag || '日常' }} ·
                    {{
                      p.media[0]?.kind === 'video'
                        ? '视频'
                        : `${p.media.length} 张照片`
                    }}</span
                  >
                </div>
                <p>{{ p.content || '这一刻，没有文字。' }}</p>
                <button
                  class="text-button"
                  title="查看记录与评论"
                  @click="open(p, p.media[0], $event, true)"
                >
                  <MessageCircle :size="16" />{{ p.comment_count
                  }}<ArrowUpRight :size="16" />
                </button>
              </div>
            </article>
          </div>
        </div></section
    ></template>
    <div v-if="!loading && !error && !filtered.length" class="empty-state">
      {{
        auth.currentCircleId
          ? '还没有时间轴记录，留下第一段回忆吧。'
          : '建立或加入圈子，开始记录。'
      }}
    </div>
    <div v-if="!loading && !error && filtered.length" class="collection-end">
      <span></span>每一天，都有迹可循。<span></span>
    </div>
    <div
      v-if="lineModal"
      v-dialog="() => (lineModal = false)"
      class="modal open"
      @click.self="lineModal = false"
    >
      <form class="modal-card narrow" @submit.prevent="saveLine">
        <div class="modal-head">
          <strong>{{ editingLine ? '编辑时间线' : '新建时间线' }}</strong
          ><button
            type="button"
            class="icon-button"
            title="关闭"
            aria-label="关闭"
            @click="lineModal = false"
          >
            <X />
          </button>
        </div>
        <div class="line-form">
          <label
            >名称<input
              v-model="lineForm.title"
              required
              maxlength="64"
              placeholder="例如：我们的云南之旅" /></label
          ><label
            >类型<select v-model="lineForm.kind" aria-label="时间线类型">
              <option
                v-for="(label, value) in kindLabels"
                :key="value"
                :value="value"
              >
                {{ label }}
              </option>
            </select></label
          ><label
            >归属主线<select v-model="lineForm.parent_id">
              <option :value="null">汇总主线</option>
              <option
                v-for="line in parentOptions"
                :key="line.id"
                :value="line.id"
              >
                {{ line.title }}
              </option>
            </select></label
          >
          <fieldset class="album-checkboxes">
            <legend>关联分册</legend>
            <label v-for="a in editableAlbums" :key="a.id"
              ><input
                v-model="lineForm.albumIds"
                type="checkbox"
                :value="a.id"
              />{{ a.title }}</label
            >
            <p v-if="!editableAlbums.length" class="muted">
              还没有可关联的分册。
            </p>
          </fieldset>
          <p v-if="lineError" class="error-message">{{ lineError }}</p>
          <button
            class="primary"
            :disabled="lineBusy || !lineForm.title.trim()"
          >
            {{ lineBusy ? '保存中…' : '保存时间线' }}
          </button>
        </div>
      </form>
    </div>
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
  reactive,
  ref,
  watch,
} from 'vue'
import {
  ArrowUpRight,
  GitBranch,
  MapPin,
  MessageCircle,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import MediaPreview from '../components/MediaPreview.vue'
import FootprintMap from '../components/FootprintMap.vue'
import MemoryNavigator from '../components/MemoryNavigator.vue'
import { confirmDialog } from '../utils/confirm'
const emit = defineEmits(['open-post'])
const auth = useAuthStore(),
  revision = inject('revision')
const months = ref([]),
  year = ref('all'),
  activeMonth = ref(''),
  root = ref(null),
  loading = ref(true),
  error = ref('')
const navigation = ref(null),
  navigationHeight = ref(0),
  activePostId = ref(null)
const lines = ref([]),
  albums = ref([]),
  selectedLine = ref(null),
  mode = ref('stories'),
  lineModal = ref(false),
  editingLine = ref(null),
  lineBusy = ref(false),
  lineError = ref('')
const lineForm = reactive({
  title: '',
  kind: 'life',
  parent_id: null,
  albumIds: [],
})
const kindLabels = {
  life: '生活',
  travel: '旅行',
  graduation: '毕业',
  other: '其他',
}
const currentLine = computed(() =>
  lines.value.find((l) => l.id === selectedLine.value),
)
const canManage = computed(
  () =>
    currentLine.value &&
    (currentLine.value.created_by === auth.user?.id || auth.canManage),
)
const parentLabel = computed(
  () =>
    lines.value.find((l) => l.id === currentLine.value?.parent_id)?.title ||
    '汇总主线',
)
const allCount = computed(() =>
  months.value.reduce((n, m) => n + m.post_count, 0),
)
const orderedLines = computed(() => {
  const result = []
  function walk(parent, depth) {
    for (const line of lines.value.filter((l) => l.parent_id === parent)) {
      result.push({ ...line, depth })
      walk(line.id, depth + 1)
    }
  }
  walk(null, 0)
  return result
})
function children(id) {
  const ids = new Set([id])
  let size = -1
  while (size !== ids.size) {
    size = ids.size
    lines.value.forEach((l) => {
      if (ids.has(l.parent_id)) ids.add(l.id)
    })
  }
  return ids
}
const parentOptions = computed(() =>
  editingLine.value
    ? orderedLines.value.filter((l) => !children(editingLine.value).has(l.id))
    : orderedLines.value,
)
const editableAlbums = computed(() =>
  albums.value.filter((a) => a.created_by === auth.user?.id || auth.canManage),
)
const monthNames = [
  '一月',
  '二月',
  '三月',
  '四月',
  '五月',
  '六月',
  '七月',
  '八月',
  '九月',
  '十月',
  '十一月',
  '十二月',
]
const years = computed(() => [...new Set(months.value.map((m) => m.year))])
const filtered = computed(() => {
  const ids = selectedLine.value ? children(selectedLine.value) : null
  return months.value
    .filter((m) => year.value === 'all' || m.year === year.value)
    .map((m) => {
      const days = m.days
        .map((d) => ({
          ...d,
          posts: d.posts.filter((p) => !ids || ids.has(p.line_id)),
        }))
        .filter((d) => d.posts.length)
      return {
        ...m,
        days,
        post_count: days.reduce((n, d) => n + d.posts.length, 0),
      }
    })
    .filter((m) => m.days.length)
})
const mapPosts = computed(() =>
  filtered.value.flatMap((m) => m.days.flatMap((d) => d.posts)),
)
const total = computed(() =>
  filtered.value.reduce((n, m) => n + m.post_count, 0),
)
const key = (m) => `${m.year}-${m.month}`
const featured = (m) =>
  m.days
    .flatMap((d) => d.posts)
    .find((p) => p.media.some((media) => media.kind === 'photo'))?.id
const weekday = (s) =>
  new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(
    new Date(`${s}T12:00:00`),
  )
let seq = 0,
  loadedRevision = -1,
  scroller,
  frame,
  observer,
  navigationObserver,
  active = false
function open(p, media, event, comments = false) {
  emit('open-post', {
    id: p.id,
    mediaId: media?.id,
    source: event.currentTarget.querySelector('img'),
    comments,
  })
}
function updateMonth() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    if (!active || !root.value || !scroller) return
    const top = scroller.getBoundingClientRect().top + scrollInset() + 32
    const chapters = [...root.value.querySelectorAll('[data-month]')]
    const current =
      chapters.filter((el) => el.getBoundingClientRect().top <= top).at(-1) ||
      chapters[0]
    activeMonth.value = current?.dataset.month || ''
    const stories = [...root.value.querySelectorAll('[data-story]')]
    const atEnd =
      scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4
    const story = atEnd
      ? stories.at(-1)
      : stories.filter((el) => el.getBoundingClientRect().top <= top).at(-1) ||
        stories[0]
    activePostId.value = story ? Number(story.dataset.story) : null
  })
}
function scrollInset() {
  const padding = scroller
    ? parseFloat(getComputedStyle(scroller).paddingTop)
    : 0
  const heading =
    root.value?.querySelector('.chapter-heading')?.getBoundingClientRect()
      .height || 0
  return Math.max(0, navigationHeight.value - padding) + heading + 12
}
function scrollToElement(target, inset) {
  if (!scroller || !target) return
  scroller.scrollTo({
    top:
      scroller.scrollTop +
      target.getBoundingClientRect().top -
      scroller.getBoundingClientRect().top -
      inset,
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches
      ? 'instant'
      : 'smooth',
  })
}
function goToPost(id) {
  const target = root.value?.querySelector(`[data-story="${id}"]`)
  if (!target) return
  activePostId.value = id
  target.classList.add('is-visible')
  scrollToElement(target, scrollInset())
}
function openCurrent(p) {
  if (!p) return
  emit('open-post', {
    id: p.id,
    mediaId: p.media[0]?.id,
    source: root.value?.querySelector(
      `[data-story="${p.id}"] .chronicle-images img`,
    ),
  })
}
function jump(m) {
  const target = root.value?.querySelector(`[data-month="${key(m)}"]`)
  scrollToElement(
    target,
    Math.max(
      0,
      navigationHeight.value -
        parseFloat(getComputedStyle(scroller).paddingTop),
    ),
  )
  activeMonth.value = key(m)
}
async function observe() {
  await nextTick()
  observer?.disconnect()
  navigationObserver?.disconnect()
  if (!active) return
  if (navigation.value) {
    navigationHeight.value = navigation.value.getBoundingClientRect().height
    navigationObserver = new ResizeObserver(() => {
      navigationHeight.value =
        navigation.value?.getBoundingClientRect().height || 0
      updateMonth()
    })
    navigationObserver.observe(navigation.value)
  } else navigationHeight.value = 0
  observer = new IntersectionObserver(
    (entries) =>
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('is-visible')
          observer.unobserve(e.target)
        }
      }),
    { root: scroller, rootMargin: '0px 0px 60px 0px' },
  )
  root.value
    ?.querySelectorAll('.chronicle-story')
    .forEach((el) => observer.observe(el))
  updateMonth()
}
async function load() {
  const request = ++seq,
    circle = auth.currentCircleId
  loading.value = !!circle && !months.value.length
  error.value = ''
  if (!circle) {
    months.value = []
    loading.value = false
    return
  }
  try {
    const [m, l, a] = await Promise.all([
      api.get(`/api/circles/${circle}/timeline`),
      api.get(`/api/circles/${circle}/lines`),
      api.get(`/api/circles/${circle}/albums`),
    ])
    if (request !== seq || circle !== auth.currentCircleId) return
    months.value = m.data
    lines.value = l.data
    albums.value = a.data
    if (
      selectedLine.value &&
      !lines.value.some((l) => l.id === selectedLine.value)
    )
      selectedLine.value = null
    loadedRevision = revision.value
  } catch (e) {
    if (request === seq) error.value = e.userMessage || '加载时间线失败'
  } finally {
    if (request === seq) loading.value = false
  }
  observe()
}
onActivated(() => {
  active = true
  scroller = root.value.closest('.body-grid')
  scroller.addEventListener('scroll', updateMonth, { passive: true })
  if (loadedRevision !== revision.value) load()
  else observe()
})
function cleanup() {
  active = false
  lineModal.value = false
  scroller?.removeEventListener('scroll', updateMonth)
  observer?.disconnect()
  navigationObserver?.disconnect()
  cancelAnimationFrame(frame)
}
onDeactivated(cleanup)
onBeforeUnmount(cleanup)
watch([year, selectedLine, mode], async () => {
  await observe()
  scroller?.scrollTo({ top: 0, behavior: 'instant' })
})
watch(revision, () => {
  if (active) load()
})
function newLine() {
  editingLine.value = null
  Object.assign(lineForm, {
    title: '',
    kind: 'life',
    parent_id: selectedLine.value,
    albumIds: [],
  })
  lineError.value = ''
  lineModal.value = true
}
function editLine() {
  editingLine.value = currentLine.value.id
  Object.assign(lineForm, {
    title: currentLine.value.title,
    kind: currentLine.value.kind,
    parent_id: currentLine.value.parent_id,
    albumIds: editableAlbums.value
      .filter((a) => a.line_id === currentLine.value.id)
      .map((a) => a.id),
  })
  lineError.value = ''
  lineModal.value = true
}
async function saveLine() {
  if (lineBusy.value) return
  lineBusy.value = true
  lineError.value = ''
  try {
    const payload = {
      title: lineForm.title.trim(),
      kind: lineForm.kind,
      parent_id: lineForm.parent_id,
    }
    let id = editingLine.value
    if (id)
      await api.patch(
        `/api/circles/${auth.currentCircleId}/lines/${id}`,
        payload,
      )
    else {
      const { data } = await api.post(
        `/api/circles/${auth.currentCircleId}/lines`,
        payload,
      )
      id = data.id
      editingLine.value = id
    }
    for (const a of editableAlbums.value) {
      const want = lineForm.albumIds.includes(a.id)
      if ((want && a.line_id !== id) || (!want && a.line_id === id))
        await api.patch(`/api/circles/${auth.currentCircleId}/albums/${a.id}`, {
          line_id: want ? id : null,
        })
    }
    selectedLine.value = id
    lineModal.value = false
    revision.value++
  } catch (e) {
    lineError.value = e.userMessage || '保存失败，可重试'
  } finally {
    lineBusy.value = false
  }
}
async function removeLine() {
  if (lineBusy.value) return
  if (
    !(await confirmDialog({
      title: '删除时间线',
      message: '分册与记录会保留，子分支将归入上级主线。',
      confirmText: '删除时间线',
      danger: true,
    }))
  )
    return
  lineBusy.value = true
  try {
    await api.delete(
      `/api/circles/${auth.currentCircleId}/lines/${selectedLine.value}`,
    )
    selectedLine.value = null
    revision.value++
  } catch (e) {
    error.value = e.userMessage || '删除失败'
  } finally {
    lineBusy.value = false
  }
}
</script>
