<template>
  <Teleport to="body">
    <div
      class="gsearch-layer"
      role="dialog"
      aria-modal="true"
      aria-label="搜索回忆"
      @click.self="close"
    >
      <section class="gsearch-panel">
        <header class="gsearch-head">
          <Search class="gsearch-glyph" :size="18" />
          <input
            ref="inputEl"
            v-model="q"
            class="gsearch-input"
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            placeholder="搜索文字、地点、标签…"
            aria-label="搜索关键字"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="commit"
          />
          <kbd v-if="!isMobile" class="gsearch-kbd">Ctrl K</kbd>
          <button class="gsearch-close" type="button" aria-label="关闭搜索" @click="close">
            <X :size="18" />
          </button>
        </header>

        <div class="gsearch-filters">
          <div class="gsearch-chips" role="group" aria-label="记录类型">
            <button
              v-for="option in kindOptions"
              :key="option.value"
              type="button"
              class="gsearch-chip"
              :class="{ active: kind === option.value }"
              :aria-pressed="kind === option.value"
              @click="kind = option.value"
            >
              {{ option.label }}
            </button>
          </div>

          <div class="gsearch-chips" role="group" aria-label="圈子">
            <button
              type="button"
              class="gsearch-chip"
              :class="{ active: circleId === null }"
              @click="setCircle(null)"
            >
              全部圈子
            </button>
            <button
              v-for="circle in circles"
              :key="circle.id"
              type="button"
              class="gsearch-chip"
              :class="{ active: circleId === circle.id }"
              @click="setCircle(circle.id)"
            >
              {{ circle.name }}
            </button>
          </div>

          <div class="gsearch-more-row">
            <button
              type="button"
              class="gsearch-more"
              :aria-expanded="moreOpen"
              @click="moreOpen = !moreOpen"
            >
              <SlidersHorizontal :size="13" />日期与成员
            </button>
            <button v-if="hasFilters" type="button" class="gsearch-reset" @click="resetFilters">
              清除筛选
            </button>
            <span class="gsearch-count">{{ loading ? '搜索中…' : `共 ${total} 条记录` }}</span>
          </div>

          <div v-if="moreOpen" class="gsearch-more-grid">
            <label>
              <span>开始日期</span>
              <input v-model="dateFrom" type="date" />
            </label>
            <label>
              <span>结束日期</span>
              <input v-model="dateTo" type="date" />
            </label>
            <label v-if="circleId">
              <span>成员</span>
              <select v-model="memberId">
                <option :value="null">全部成员</option>
                <option v-for="member in members" :key="member.user_id" :value="member.user_id">
                  {{ member.nickname || member.username }}
                </option>
              </select>
            </label>
          </div>
        </div>

        <div class="gsearch-body">
          <div v-if="loading && !posts.length" class="gsearch-skeleton" aria-hidden="true">
            <div v-for="n in 4" :key="n" class="gsearch-skeleton-row"><i></i><span></span></div>
          </div>

          <p v-else-if="error" class="gsearch-state" role="alert">{{ error }}</p>

          <template v-else-if="posts.length || albums.length">
            <div v-if="albums.length" class="gsearch-group">
              <h3>主题分册</h3>
              <button
                v-for="album in albums"
                :key="`a-${album.id}`"
                type="button"
                class="gsearch-album"
                @click="openAlbum(album)"
              >
                <BookOpen :size="16" />
                <span class="gsearch-album-main">
                  <strong>{{ album.title }}</strong>
                  <small>{{ album.circle_name }} · {{ album.post_count }} 条记录<template v-if="album.prompt"> · {{ album.prompt }}</template></small>
                </span>
                <CornerDownLeft :size="13" />
              </button>
            </div>

            <div class="gsearch-group">
              <h3 v-if="albums.length">记录</h3>
              <button
                v-for="(item, index) in posts"
                :key="item.id"
                type="button"
                class="gsearch-item"
                :class="{ active: cursor === index }"
                @mouseenter="cursor = index"
                @click="openPost(item)"
              >
                <span class="gsearch-thumb">
                  <img v-if="item.preview_url" :src="item.preview_url" alt="" loading="lazy" decoding="async" />
                  <component :is="thumbIcon(item)" v-else :size="18" />
                  <i v-if="item.kinds.includes('audio')" class="gsearch-thumb-audio"><Mic :size="9" /></i>
                </span>
                <span class="gsearch-item-main">
                  <span class="gsearch-item-title">
                    <template
                      v-for="(seg, i) in highlight(item.location_name || plainSnippet(item) || '无文字记录')"
                      :key="i"
                    >
                      <mark v-if="seg.hit">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </span>
                  <span v-if="item.location_name && item.snippet" class="gsearch-item-snippet">
                    <template v-for="(seg, i) in highlight(item.snippet)" :key="i">
                      <mark v-if="seg.hit">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </span>
                  <span class="gsearch-item-meta">
                    <time :datetime="item.event_date">{{ shortDate(item.event_date) }}</time>
                    <span>{{ item.circle_name }}</span>
                    <span>{{ item.author_name }}</span>
                    <span v-if="item.activity_tag" class="gsearch-tag">{{ item.activity_tag }}</span>
                    <span v-if="item.media_count > 1" class="gsearch-tag">{{ item.media_count }} 个文件</span>
                  </span>
                </span>
                <CornerDownLeft class="gsearch-item-enter" :size="13" />
              </button>
            </div>

            <button v-if="posts.length < total" type="button" class="gsearch-load" :disabled="loadingMore" @click="loadMore">
              {{ loadingMore ? '加载中…' : `加载更多（还有 ${total - posts.length} 条）` }}
            </button>
          </template>

          <p v-else class="gsearch-state">
            <template v-if="q.trim()">没有找到「{{ q.trim() }}」，换个词或放宽筛选试试。</template>
            <template v-else>输入关键字开始搜索，也可以只用下面的筛选条件浏览。</template>
          </p>
        </div>

        <footer class="gsearch-foot">
          <span v-if="tags.length" class="gsearch-suggests">
            常搜标签
            <button v-for="tag in tags.slice(0, 5)" :key="tag" type="button" @click="q = tag">{{ tag }}</button>
          </span>
          <span v-else class="gsearch-hint">↑↓ 选择 · Enter 打开 · Esc 关闭</span>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  AlignLeft,
  BookOpen,
  CornerDownLeft,
  FileText,
  Film,
  Image as ImageIcon,
  Mic,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-vue-next'
import api from '../api'

const props = defineProps({
  circles: { type: Array, default: () => [] },
  circleId: { type: Number, default: null },
})
const emit = defineEmits(['close', 'open-post', 'open-album'])

const kindOptions = [
  { value: '', label: '全部' },
  { value: 'photo', label: '照片' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '语音' },
  { value: 'text', label: '纯文字' },
]

const inputEl = ref(null)
const q = ref('')
const kind = ref('')
const circleId = ref(props.circleId)
const dateFrom = ref('')
const dateTo = ref('')
const memberId = ref(null)
const moreOpen = ref(false)
const posts = ref([])
const albums = ref([])
const tags = ref([])
const total = ref(0)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const cursor = ref(0)
const members = ref([])
const isMobile = ref(
  typeof window !== 'undefined' && window.matchMedia('(max-width: 650px)').matches,
)

const hasFilters = computed(
  () => kind.value || circleId.value !== null || dateFrom.value || dateTo.value || memberId.value != null,
)

let seq = 0
let timer = null
let controller = null

function shortDate(value) {
  return value ? value.replaceAll('-', '.') : ''
}

function plainSnippet(item) {
  return item.snippet || item.content?.slice(0, 60) || ''
}

function thumbIcon(item) {
  if (item.kinds.includes('video')) return Film
  if (item.kinds.includes('audio')) return Mic
  if (item.kinds.includes('photo')) return ImageIcon
  return AlignLeft
}

function highlight(text) {
  const keyword = q.value.trim()
  if (!keyword || !text) return [{ text: text || '', hit: false }]
  const source = String(text)
  const lower = source.toLowerCase()
  const target = keyword.toLowerCase()
  const parts = []
  let at = 0
  while (at < source.length) {
    const found = lower.indexOf(target, at)
    if (found < 0) {
      parts.push({ text: source.slice(at), hit: false })
      break
    }
    if (found > at) parts.push({ text: source.slice(at, found), hit: false })
    parts.push({ text: source.slice(found, found + keyword.length), hit: true })
    at = found + keyword.length
  }
  return parts.length ? parts : [{ text: source, hit: false }]
}

async function load({ append = false } = {}) {
  const current = ++seq
  controller?.abort()
  controller = new AbortController()
  if (append) loadingMore.value = true
  else {
    loading.value = true
    cursor.value = 0
  }
  error.value = ''
  try {
    const { data } = await api.get('/api/search', {
      params: {
        q: q.value.trim(),
        kind: kind.value || undefined,
        circle_id: circleId.value ?? undefined,
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined,
        member_id: memberId.value ?? undefined,
        limit: 20,
        offset: append ? posts.value.length : 0,
      },
      signal: controller.signal,
    })
    if (current !== seq) return
    posts.value = append ? [...posts.value, ...data.posts] : data.posts
    albums.value = append ? albums.value : data.albums
    tags.value = data.tags || []
    total.value = data.total
  } catch (e) {
    if (e?.code === 'ERR_CANCELED' || e?.name === 'CanceledError') return
    if (current === seq) error.value = e.userMessage || '搜索失败，请稍后重试'
  } finally {
    if (current === seq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function schedule() {
  clearTimeout(timer)
  timer = setTimeout(() => load(), 260)
}

watch(q, schedule)
watch([kind, circleId, dateFrom, dateTo, memberId], () => load())

watch(circleId, async (id) => {
  memberId.value = null
  members.value = []
  if (!id) return
  try {
    const { data } = await api.get(`/api/circles/${id}/members`)
    members.value = Array.isArray(data) ? data : data.items || []
  } catch {
    members.value = []
  }
})

function setCircle(id) {
  circleId.value = id
}

function resetFilters() {
  kind.value = ''
  circleId.value = null
  dateFrom.value = ''
  dateTo.value = ''
  memberId.value = null
}

function move(step) {
  if (!posts.value.length) return
  cursor.value = (cursor.value + step + posts.value.length) % posts.value.length
  nextTick(() => {
    document
      .querySelector(`.gsearch-item:nth-of-type(${cursor.value + 1})`)
      ?.scrollIntoView({ block: 'nearest' })
  })
}

function commit() {
  const target = posts.value[cursor.value]
  if (target) openPost(target)
}

function openPost(item) {
  emit('open-post', { id: item.id, mediaId: item.media_id ?? undefined })
}

function openAlbum(album) {
  emit('open-album', album)
}

function loadMore() {
  if (loadingMore.value) return
  load({ append: true })
}

function close() {
  emit('close')
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    close()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown, true)
  document.documentElement.classList.add('gsearch-lock')
  await nextTick()
  inputEl.value?.focus()
  load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown, true)
  document.documentElement.classList.remove('gsearch-lock')
  clearTimeout(timer)
  controller?.abort()
})
</script>

<style scoped>
.gsearch-layer {
  position: fixed;
  inset: 0;
  z-index: 86;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 8vh 20px 24px;
  background: rgba(16, 20, 19, 0.5);
  backdrop-filter: blur(3px);
  animation: gsearch-fade 0.16s ease-out;
}
@keyframes gsearch-fade {
  from {
    opacity: 0;
  }
}
.gsearch-panel {
  width: min(720px, 100%);
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  color: var(--ink);
  box-shadow: var(--shadow-lg);
  animation: gsearch-rise 0.2s var(--ease-out);
}
@keyframes gsearch-rise {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.99);
  }
}
.gsearch-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}
.gsearch-glyph {
  color: var(--muted);
  flex: none;
}
.gsearch-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--ink);
  font-size: 15px;
  font-family: inherit;
  outline: none;
}
.gsearch-input::placeholder {
  color: var(--muted);
}
.gsearch-input::-webkit-search-cancel-button {
  display: none;
}
.gsearch-kbd {
  flex: none;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 5px;
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 0.02em;
}
.gsearch-close {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, var(--ink) 6%, transparent);
  color: var(--muted);
  cursor: pointer;
}
.gsearch-close:hover {
  color: var(--ink);
  background: color-mix(in srgb, var(--ink) 12%, transparent);
}
.gsearch-filters {
  display: grid;
  gap: 8px;
  padding: 10px 16px 12px;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--paper) 62%, var(--surface));
}
.gsearch-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 1px;
}
.gsearch-chips::-webkit-scrollbar {
  display: none;
}
.gsearch-chip {
  flex: none;
  padding: 4px 11px;
  border: 1px solid var(--line);
  border-radius: 99px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--t-fast) ease, color var(--t-fast) ease,
    border-color var(--t-fast) ease;
}
.gsearch-chip:hover {
  border-color: var(--terracotta);
  color: var(--ink);
}
.gsearch-chip.active {
  border-color: transparent;
  background: var(--terracotta);
  color: #fff;
  font-weight: 600;
}
.gsearch-more-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gsearch-more {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border: 1px dashed var(--line);
  border-radius: 5px;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
}
.gsearch-more[aria-expanded='true'] {
  border-style: solid;
  border-color: var(--terracotta);
  color: var(--terracotta-dark);
}
.gsearch-reset {
  border: 0;
  background: none;
  color: var(--terracotta-dark);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  text-decoration: underline;
}
.gsearch-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--muted);
}
.gsearch-more-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 2px;
}
.gsearch-more-grid label {
  display: grid;
  gap: 3px;
  font-size: 10px;
  color: var(--muted);
}
.gsearch-more-grid input,
.gsearch-more-grid select {
  padding: 5px 7px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--ink);
  font-size: 12px;
  font-family: inherit;
  color-scheme: light dark;
}
.gsearch-body {
  flex: 1;
  min-height: 320px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 6px 0 4px;
}
.gsearch-group h3 {
  margin: 8px 16px 4px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.gsearch-album,
.gsearch-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.gsearch-album:hover,
.gsearch-item:hover,
.gsearch-item.active {
  background: color-mix(in srgb, var(--terracotta) 8%, transparent);
}
.gsearch-album > svg:first-child {
  color: var(--gold);
}
.gsearch-album-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.gsearch-album-main strong {
  font-size: 13px;
  font-weight: 600;
}
.gsearch-album-main small {
  font-size: 11px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gsearch-album > svg:last-child {
  color: var(--muted);
  opacity: 0.5;
}
.gsearch-thumb {
  position: relative;
  flex: none;
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 8px;
  background: color-mix(in srgb, var(--ink) 7%, transparent);
  color: var(--muted);
}
.gsearch-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gsearch-thumb-audio {
  position: absolute;
  right: 3px;
  bottom: 3px;
  display: grid;
  place-items: center;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: var(--terracotta);
  color: #fff;
}
.gsearch-item-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.gsearch-item-title {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gsearch-item-snippet {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gsearch-item-snippet mark,
.gsearch-item-title mark {
  padding: 0 1px;
  border-radius: 2px;
  background: color-mix(in srgb, var(--gold) 44%, transparent);
  color: var(--ink);
}
.gsearch-item-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: var(--muted);
  overflow: hidden;
  white-space: nowrap;
}
.gsearch-item-meta > span + span::before,
.gsearch-item-meta > time + span::before {
  content: '·';
  margin-right: 7px;
  opacity: 0.6;
}
.gsearch-tag {
  padding: 1px 6px;
  border-radius: 99px;
  background: color-mix(in srgb, var(--pine) 10%, transparent);
  color: var(--pine);
}
.gsearch-tag::before {
  content: none !important;
}
.gsearch-item-enter {
  flex: none;
  color: var(--muted);
  opacity: 0;
}
.gsearch-item:hover .gsearch-item-enter,
.gsearch-item.active .gsearch-item-enter {
  opacity: 0.6;
}
.gsearch-load {
  display: block;
  width: calc(100% - 32px);
  margin: 8px 16px 10px;
  padding: 9px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.gsearch-load:hover {
  border-color: var(--terracotta);
  color: var(--terracotta-dark);
}
.gsearch-state {
  margin: 0;
  padding: 42px 24px;
  text-align: center;
  font-size: 12px;
  color: var(--muted);
}
.gsearch-skeleton {
  padding: 10px 16px;
  display: grid;
  gap: 10px;
}
.gsearch-skeleton-row {
  display: flex;
  gap: 11px;
  align-items: center;
}
.gsearch-skeleton-row i {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--ink) 8%, transparent);
  animation: gsearch-pulse 1.3s ease-in-out infinite;
}
.gsearch-skeleton-row span {
  flex: 1;
  height: 30px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--ink) 6%, transparent);
  animation: gsearch-pulse 1.3s ease-in-out infinite 0.15s;
}
@keyframes gsearch-pulse {
  50% {
    opacity: 0.45;
  }
}
.gsearch-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-top: 1px solid var(--line);
  font-size: 10px;
  color: var(--muted);
  background: color-mix(in srgb, var(--paper) 62%, var(--surface));
}
.gsearch-suggests {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.gsearch-suggests button {
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 99px;
  background: var(--surface);
  color: var(--ink);
  font-size: 10px;
  font-family: inherit;
  cursor: pointer;
}
.gsearch-suggests button:hover {
  border-color: var(--terracotta);
  color: var(--terracotta-dark);
}
.gsearch-hint {
  opacity: 0.85;
}

:global(html.gsearch-lock),
:global(html.gsearch-lock body) {
  overflow: hidden;
}

@media (max-width: 650px) {
  .gsearch-layer {
    padding: 0;
    align-items: stretch;
  }
  .gsearch-panel {
    width: 100%;
    max-height: 100%;
    height: 100%;
    border: 0;
    border-radius: 0;
    animation: none;
  }
  .gsearch-head {
    padding: calc(12px + env(safe-area-inset-top)) 14px 12px;
  }
  .gsearch-input {
    font-size: 16px;
  }
  .gsearch-body {
    padding-bottom: calc(6px + env(safe-area-inset-bottom));
  }
  .gsearch-foot {
    padding-bottom: calc(9px + env(safe-area-inset-bottom));
  }
  .gsearch-item {
    padding: 11px 14px;
  }
  .gsearch-item-enter {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .gsearch-layer,
  .gsearch-panel,
  .gsearch-skeleton-row i,
  .gsearch-skeleton-row span {
    animation: none;
  }
}
</style>
