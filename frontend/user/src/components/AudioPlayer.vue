<template>
  <div class="audio-player" :class="{ playing }">
    <button
      class="audio-toggle"
      type="button"
      :title="playing ? '暂停' : '播放'"
      :aria-label="playing ? '暂停语音' : '播放语音'"
      @click="toggle"
    >
      <Pause v-if="playing" :size="18" fill="currentColor" />
      <Play v-else :size="18" fill="currentColor" />
    </button>
    <div class="audio-body">
      <div
        class="audio-wave"
        role="slider"
        :aria-valuemin="0"
        :aria-valuemax="100"
        :aria-valuenow="Math.round(percent)"
        aria-label="语音进度"
        tabindex="0"
        @click="seek"
        @keydown.left.prevent="nudge(-5)"
        @keydown.right.prevent="nudge(5)"
      >
        <span
          v-for="(h, i) in bars"
          :key="i"
          class="audio-bar"
          :class="{ on: percent >= (i + 1) * (100 / bars.length) }"
          :style="{ height: `${h}%` }"
        />
      </div>
      <div class="audio-meta">
        <span>{{ clock(time) }}</span>
        <span class="audio-name">{{ label }}</span>
        <span>{{ clock(duration) }}</span>
      </div>
    </div>
    <a
      class="audio-download"
      :href="media.download_url"
      :title="`下载 ${media.original_filename}`"
      :aria-label="`下载 ${media.original_filename}`"
      download
    >
      <Download :size="16" />
    </a>
    <audio
      ref="el"
      :src="media.original_url"
      preload="metadata"
      @loadedmetadata="onLoaded"
      @timeupdate="onTime"
      @ended="onEnded"
      @pause="playing = false"
      @play="playing = true"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Download, Pause, Play } from 'lucide-vue-next'

const props = defineProps({
  media: { type: Object, required: true },
  wave: { type: Number, default: 26 },
})

const el = ref(null)
const playing = ref(false)
const time = ref(0)
const duration = ref(Number(props.media.duration_seconds) || 0)

/* 波形由 media.id 决定，同一段语音每次形状一致 */
const bars = computed(() => {
  const seed = Number(props.media.id) || 7
  return Array.from({ length: props.wave }, (_, i) => {
    const wave = Math.sin((i + seed) * 1.7) * 0.5 + Math.sin((i + seed) * 0.6) * 0.5
    return Math.round(32 + Math.abs(wave) * 60)
  })
})
const percent = computed(() =>
  duration.value ? Math.min(100, (time.value / duration.value) * 100) : 0,
)
const label = computed(
  () => props.media.original_filename || '一段语音',
)

function clock(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
function onLoaded() {
  if (!el.value) return
  if (Number.isFinite(el.value.duration) && el.value.duration > 0)
    duration.value = el.value.duration
}
function onTime() {
  time.value = el.value?.currentTime || 0
}
function onEnded() {
  playing.value = false
  time.value = 0
  if (el.value) el.value.currentTime = 0
}
function toggle() {
  if (!el.value) return
  if (el.value.paused) {
    document.querySelectorAll('audio').forEach((a) => {
      if (a !== el.value) a.pause()
    })
    el.value.play().catch(() => {})
  } else {
    el.value.pause()
  }
}
function seek(event) {
  if (!el.value || !duration.value) return
  const box = event.currentTarget.getBoundingClientRect()
  const ratio = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
  el.value.currentTime = ratio * duration.value
  time.value = el.value.currentTime
}
function nudge(delta) {
  if (!el.value) return
  el.value.currentTime = Math.min(
    duration.value || 0,
    Math.max(0, (el.value.currentTime || 0) + delta),
  )
}
watch(
  () => props.media.original_url,
  () => {
    time.value = 0
    duration.value = Number(props.media.duration_seconds) || 0
    playing.value = false
  },
)
onBeforeUnmount(() => el.value?.pause())
</script>
