<template>
  <div class="media-preview" :class="{ 'is-video': media.kind === 'video' }">
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
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
import { Film, ImageOff, Play } from 'lucide-vue-next'
const props = defineProps({
  media: { type: Object, required: true },
  alt: { type: String, default: '' },
  eager: Boolean,
})
const failed = ref(false)
const src = ref('')
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
