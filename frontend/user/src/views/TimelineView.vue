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
      <div
        v-if="years.length"
        class="year-pills"
        role="group"
        aria-label="选择年份"
      >
        <button
          type="button"
          :class="{ active: year === 'all' }"
          @click="year = 'all'"
        >
          全部</button
        ><button
          v-for="y in years"
          :key="y"
          type="button"
          :class="{ active: year === y }"
          @click="year = y"
        >
          {{ y }}
        </button>
      </div>
    </div>
    <dl v-if="!loading && !error && filtered.length" class="chronicle-stats">
      <div>
        <dt>记录</dt>
        <dd>{{ total }}</dd>
      </div>
      <div>
        <dt>影像</dt>
        <dd>{{ mediaCount }}</dd>
      </div>
      <div>
        <dt>地点</dt>
        <dd>{{ placeCount }}</dd>
      </div>
      <div>
        <dt>月份</dt>
        <dd>{{ filtered.length }}</dd>
      </div>
      <div>
        <dt>评论</dt>
        <dd>{{ commentCount }}</dd>
      </div>
    </dl>
    <div class="line-toolbar">
      <div v-if="mode === 'map' && years.length" class="year-pills" role="group" aria-label="筛选足迹年份">
        <button type="button" :class="{ active: year === 'all' }" @click="year = 'all'">全部年份</button>
        <button v-for="mapYear in years" :key="mapYear" type="button" :class="{ active: year === mapYear }" @click="year = mapYear">{{ mapYear }}</button>
      </div>
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
    </div>
    <FootprintMap
      v-if="mode === 'map' && !loading && !error"
      :posts="mapPosts"
      :user-id="auth.user?.id"
      @open-post="$emit('open-post', $event)"
    />
    <div
      v-if="mode === 'stories' && filtered.length && !error && !loading"
      ref="navigation"
      class="chronicle-navigation"
      :class="{ 'is-compact': compactNav }"
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
      ><template v-for="m in filtered" :key="key(m)"
        ><aside
          v-if="m.firstOfYear && recapOf(m.year)"
          class="year-recap"
          :aria-label="`${m.year} 年度回顾`"
        >
          <div class="recap-year">
            <span class="recap-en">{{ m.year }} · recap</span>
            <strong>{{ m.year }}</strong>
            <small>{{ recapOf(m.year)?.summary }}</small>
          </div>
          <dl class="recap-stats">
            <div>
              <dt>记录</dt>
              <dd>{{ recapOf(m.year)?.posts }}</dd>
            </div>
            <div>
              <dt>照片</dt>
              <dd>{{ recapOf(m.year)?.photos }}</dd>
            </div>
            <div>
              <dt>城市</dt>
              <dd>{{ recapOf(m.year)?.places }}</dd>
            </div>
            <div>
              <dt>同行</dt>
              <dd>{{ recapOf(m.year)?.people }}</dd>
            </div>
            <div>
              <dt>最长连续</dt>
              <dd>
                {{ recapOf(m.year)?.longest
                }}<small>天</small>
              </dd>
            </div>
          </dl>
        </aside>
        <section
          class="month-chapter"
          :data-month="key(m)"
        >
        <header class="chapter-heading">
          <span class="chapter-number">{{
            String(m.month).padStart(2, '0')
          }}</span>
          <div class="chapter-title">
            <span class="chapter-en"
              >{{ monthEn[m.month - 1] }} · {{ m.year }}</span
            >
            <h2>
              {{ monthNames[m.month - 1]
              }}<small>{{ m.post_count }} 条记录 · {{ m.days.length }} 天</small>
            </h2>
          </div>
          <ul class="chapter-meta">
            <li v-if="m.photos">
              <ImageIcon :size="13" />{{ m.photos }} 张照片
            </li>
            <li v-if="m.videos"><Film :size="13" />{{ m.videos }} 段视频</li>
            <li v-if="m.places.length">
              <MapPin :size="13" />{{ m.places.length }} 个地点
            </li>
          </ul>
          <span class="chapter-line"></span>
        </header>
        <div v-for="d in m.days" :key="d.event_date" class="chronicle-day">
          <div class="chronicle-date">
            <span class="date-node"></span>
            <em>{{ monthEn[m.month - 1].slice(0, 3) }}</em>
            <strong>{{ Number(d.event_date.slice(8)) }}</strong
            ><span>{{ weekday(d.event_date) }}</span
            >            <span v-if="termName(d.event_date)" class="date-term">{{
              termName(d.event_date)
            }}</span>
            <span class="date-counts">
              <small>{{ d.posts.length }} 条记录</small>
              <span
                v-if="streakOf(d.event_date) > 1"
                class="streak-badge"
                >连续 {{ streakOf(d.event_date) }} 天</span
              >
            </span>
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
                  pair: p.media.length === 2,
                  triple: p.media.length > 2,
                }"
              >
                <span
                  v-if="p.id === featured(m)"
                  class="featured-flag"
                  aria-hidden="true">本月精选</span
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
                  <span class="story-author"
                    ><UserAvatar :name="p.nickname || p.username" />{{
                      p.nickname || p.username
                    }}</span
                  ><span class="story-tags">
                    <span class="story-tag">{{ p.activity_tag || '日常' }}</span>
                    <span v-if="p.location_name" class="story-tag place">
                      <MapPin :size="11" />{{ p.location_name }}
                    </span>
                  </span>
                </div>
                <p>{{ p.content || '这一刻，没有文字。' }}</p>
                <div class="story-foot">
                  <button
                    class="text-button"
                    title="查看记录与评论"
                    @click="open(p, p.media[0], $event, true)"
                  >
                    <MessageCircle :size="16" />{{ p.comment_count
                    }}<ArrowUpRight :size="16" />
                  </button>
                  <time v-if="timeLabel(p)">{{ timeLabel(p) }}</time>
                </div>
              </div>
            </article>
          </div>
        </div></section></template
    ></template>
    <div v-if="!loading && !error && !filtered.length" class="empty-state">
      {{
        auth.currentCircleId
          ? '还没有时间轴记录，留下第一段回忆吧。'
          : '建立或加入圈子，开始记录。'
      }}
    </div>
    <div v-if="!loading && !error && filtered.length" class="collection-end">
      <span></span><i class="end-seal">迹</i>每一天，都有迹可循。<span></span>
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
  ref,
  watch,
} from 'vue'
import {
  ArrowUpRight,
  Film,
  Image as ImageIcon,
  MapPin,
  MessageCircle,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import MediaPreview from '../components/MediaPreview.vue'
import FootprintMap from '../components/FootprintMap.vue'
import MemoryNavigator from '../components/MemoryNavigator.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { solarTerm, streakInfo } from '../utils/calendar'
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
  activePostId = ref(null),
  compactNav = ref(false)
const mode = ref('stories')
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
const monthEn = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]
const years = computed(() => [...new Set(months.value.map((m) => m.year))])
const filtered = computed(() =>
  months.value
    .filter((m) => year.value === 'all' || m.year === year.value)
    .map((m, index, list) => {
      const posts = m.days.flatMap((d) => d.posts)
      return {
        ...m,
        firstOfYear: list.findIndex((x) => x.year === m.year) === index,
        post_count: posts.length,
        photos: posts.reduce(
          (n, p) => n + p.media.filter((x) => x.kind === 'photo').length,
          0,
        ),
        videos: posts.reduce(
          (n, p) => n + p.media.filter((x) => x.kind === 'video').length,
          0,
        ),
        places: [...new Set(posts.map((p) => p.location_name).filter(Boolean))],
      }
    })
    .filter((m) => m.days.length),
)
const recaps = computed(() => {
  const buckets = new Map()
  for (const m of filtered.value) {
    if (!buckets.has(m.year))
      buckets.set(m.year, {
        year: m.year,
        posts: 0,
        photos: 0,
        videos: 0,
        days: 0,
        places: new Set(),
        people: new Set(),
        dates: [],
      })
    const r = buckets.get(m.year)
    for (const d of m.days) {
      r.dates.push(d.event_date)
      r.days += 1
      r.posts += d.posts.length
      for (const p of d.posts) {
        r.photos += p.media.filter((x) => x.kind === 'photo').length
        r.videos += p.media.filter((x) => x.kind === 'video').length
        if (p.location_name) r.places.add(p.location_name)
        r.people.add(p.user_id)
      }
    }
  }
  return [...buckets.values()].map((r) => {
    const { longest } = streakInfo(r.dates)
    const bits = [`${r.days} 天里有记录`, `${r.photos + r.videos} 个影像`]
    if (r.places.size) bits.push(`${r.places.size} 个地方`)
    if (longest > 1) bits.push(`最长连续 ${longest} 天`)
    return {
      year: r.year,
      posts: r.posts,
      photos: r.photos + r.videos,
      places: r.places.size,
      people: r.people.size,
      longest,
      summary: bits.join(' · '),
    }
  })
})
const recapOf = (y) => recaps.value.find((r) => r.year === y)
const mapPosts = computed(() =>
  filtered.value.flatMap((m) => m.days.flatMap((d) => d.posts)),
)
const total = computed(() =>
  filtered.value.reduce((n, m) => n + m.post_count, 0),
)
const mediaCount = computed(() =>
  mapPosts.value.reduce((n, p) => n + p.media.length, 0),
)
const placeCount = computed(
  () => new Set(mapPosts.value.map((p) => p.location_name).filter(Boolean)).size,
)
const commentCount = computed(() =>
  mapPosts.value.reduce((n, p) => n + p.comment_count, 0),
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
const termName = (s) => solarTerm(s)?.name || ''
const streaks = computed(() => streakInfo(mapPosts.value.map((p) => p.event_date)))
const streakOf = (s) => streaks.value.map[s] || 0
function step(delta) {
  const list = mapPosts.value
  if (!list.length) return
  const at = list.findIndex((p) => p.id === activePostId.value)
  const next =
    at < 0
      ? list[delta > 0 ? 0 : list.length - 1]
      : list[Math.min(list.length - 1, Math.max(0, at + delta))]
  if (next) goToPost(next.id)
}
function onKey(event) {
  if (event.metaKey || event.ctrlKey || event.altKey) return
  if (mode.value !== 'stories' || !mapPosts.value.length) return
  const el = event.target
  if (
    el?.tagName === 'INPUT' ||
    el?.tagName === 'TEXTAREA' ||
    el?.isContentEditable
  )
    return
  if (document.querySelector('.record-backdrop, .modal')) return
  const delta = { j: 1, k: -1, ArrowDown: 1, ArrowUp: -1 }[event.key]
  if (!delta) return
  event.preventDefault()
  step(delta)
}
function timeLabel(p) {
  const t = new Date(p.created_at)
  return Number.isNaN(t.getTime())
    ? ''
    : new Intl.DateTimeFormat('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      }).format(t)
}
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
    compactNav.value = scroller.scrollTop > 180
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
  const headingEl = root.value?.querySelector('.chapter-heading')
  // 章节头不吸顶时不占用偏移
  const heading =
    headingEl && getComputedStyle(headingEl).position === 'sticky'
      ? headingEl.getBoundingClientRect().height || 0
      : 0
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
    const { data } = await api.get(`/api/circles/${circle}/timeline`)
    if (request !== seq || circle !== auth.currentCircleId) return
    months.value = data
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
  window.addEventListener('keydown', onKey)
  if (loadedRevision !== revision.value) load()
  else observe()
})
function cleanup() {
  active = false
  scroller?.removeEventListener('scroll', updateMonth)
  window.removeEventListener('keydown', onKey)
  observer?.disconnect()
  navigationObserver?.disconnect()
  cancelAnimationFrame(frame)
}
onDeactivated(cleanup)
onBeforeUnmount(cleanup)
watch([year, mode], async () => {
  await observe()
  scroller?.scrollTo({ top: 0, behavior: 'instant' })
})
watch(revision, () => {
  if (active) load()
})
</script>
