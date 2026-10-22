<template>
  <div class="media-preview" :class="{ 'is-video': media.kind === 'video', 'is-audio': media.kind === 'audio' }">
    <template v-if="media.kind === 'audio'">
      <div class="audio-tile">
        <span class="audio-tile-icon"><AudioLines :size="26" /></span>
        <span class="audio-tile-bars" aria-hidden="true">
          <i v-for="(h, i) in tickBars" :key="i" :style="{ height: `${h}%` }" />
        </span>
        <small>{{ durationLabel }}</small>
      </div>
    </template>
    <template v-else>
      <img
        v-if="src && !failed"
        :src="src"
        :alt="alt"
        :loading="eager ? 'eager' : 'lazy'"
        decoding="async"
        @error="fallback"
      />
      <div v-else class="media-placeholder">
        <component
          :is="media.kind === 'video' ? Film : ImageOff"
          :size="28"
        /><span>{{ media.kind === 'video' ? '视频' : '图片暂不可用' }}</span>
      </div>
      <span v-if="media.kind === 'video'" class="play-mark"
        ><Play :size="20" fill="currentColor"
      /></span>
    </template>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { AudioLines, Film, ImageOff, Play } from 'lucide-vue-next'
const props = defineProps({
  media: { type: Object, required: true },
  alt: { type: String, default: '' },
  eager: Boolean,
})
const failed = ref(false)
const src = ref('')
const tickBars = computed(() => {
  const seed = Number(props.media.id) || 3
  return Array.from({ length: 9 }, (_, i) =>
    Math.round(28 + Math.abs(Math.sin((i + seed) * 1.9)) * 62),
  )
})
const durationLabel = computed(() => {
  const total = Math.round(Number(props.media.duration_seconds) || 0)
  return total ? `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}` : '语音'
})
watch(
  () => props.media,
  (m) => {
    src.value = m.preview_url || (m.kind === 'photo' ? m.original_url : '')
    failed.value = false
  },
  { immediate: true },
)
function fallback() {
  if (props.media.kind === 'photo' && src.value !== props.media.original_url)
    src.value = props.media.original_url
  else failed.value = true
}
</script>
