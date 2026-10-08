<template>
  <div class="memory-navigator" aria-label="回忆导航" @keydown="keydown">
    <div class="memory-controls">
      <div class="memory-position">
        <strong>{{ current?.event_date || '' }}</strong>
        <span>{{ index + 1 }} / {{ posts.length }}</span>
      </div>
      <div class="memory-actions">
        <button
          class="icon-button"
          title="上一刻"
          aria-label="上一刻"
          :disabled="index <= 0"
          @click="step(-1)"
        >
          <ChevronLeft :size="18" />
        </button>
        <button
          class="icon-button"
          title="下一刻"
          aria-label="下一刻"
          :disabled="index >= posts.length - 1"
          @click="step(1)"
        >
          <ChevronRight :size="18" />
        </button>
        <button
          class="icon-button"
          title="随机回忆"
          aria-label="随机回忆"
          :disabled="posts.length < 2"
          @click="shuffle"
        >
          <Shuffle :size="17" />
        </button>
        <button
          class="icon-button"
          title="打开这一刻"
          aria-label="打开这一刻"
          :disabled="!current"
          @click="emit('open', current)"
        >
          <ArrowUpRight :size="18" />
        </button>
        <button
          class="icon-button"
          :title="expanded ? '收起照片导航' : '展开照片导航'"
          :aria-label="expanded ? '收起照片导航' : '展开照片导航'"
          :aria-expanded="expanded"
          @click="expanded = !expanded"
        >
          <GalleryHorizontalEnd :size="17" />
        </button>
      </div>
    </div>
    <nav
      v-if="expanded"
      ref="strip"
      class="memory-strip"
      aria-label="照片胶片导航"
    >
      <button
        v-for="p in posts"
        :key="p.id"
        :data-memory-id="p.id"
        :class="{ 'is-current': p.id === current?.id }"
        :aria-current="p.id === current?.id ? 'true' : undefined"
        :aria-label="`定位 ${p.event_date} ${p.nickname || p.username} 的记录`"
        :title="`${p.event_date} · ${p.content || '这一刻'}`"
        @click="emit('navigate', p.id)"
      >
        <MediaPreview v-if="p.media.length" :media="p.media[0]" />
        <span v-else class="memory-text-preview"><PenLine :size="20" /></span>
        <small>{{ p.event_date.slice(5).replace('-', '/') }}</small>
      </button>
    </nav>
    <div class="memory-progress" aria-hidden="true">
      <span :style="{ width: `${((index + 1) / posts.length) * 100}%` }" />
    </div>
  </div>
</template>
<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  GalleryHorizontalEnd,
  PenLine,
  Shuffle,
} from 'lucide-vue-next'
import MediaPreview from './MediaPreview.vue'
const props = defineProps({
  posts: { type: Array, required: true },
  activeId: { type: Number, default: null },
})
const emit = defineEmits(['navigate', 'open'])
const strip = ref(null),
  expanded = ref(true)
const index = computed(() =>
  Math.max(
    0,
    props.posts.findIndex((p) => p.id === props.activeId),
  ),
)
const current = computed(() => props.posts[index.value])
function step(delta) {
  const post = props.posts[index.value + delta]
  if (post) emit('navigate', post.id)
}
function shuffle() {
  if (props.posts.length < 2) return
  const next =
    (index.value + 1 + Math.floor(Math.random() * (props.posts.length - 1))) %
    props.posts.length
  emit('navigate', props.posts[next].id)
}
function keydown(event) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
  event.preventDefault()
  step(event.key === 'ArrowLeft' ? -1 : 1)
}
watch(
  [() => props.activeId, () => props.posts, expanded],
  async () => {
    await nextTick()
    const target = strip.value?.querySelector(
      `[data-memory-id="${current.value?.id}"]`,
    )
    if (!target) return
    if (
      target.offsetLeft >= strip.value.scrollLeft &&
      target.offsetLeft + target.clientWidth <=
        strip.value.scrollLeft + strip.value.clientWidth
    )
      return
    strip.value.scrollTo({
      left:
        target.offsetLeft -
        strip.value.clientWidth / 2 +
        target.clientWidth / 2,
      behavior: 'instant',
    })
  },
  { immediate: true },
)
</script>
