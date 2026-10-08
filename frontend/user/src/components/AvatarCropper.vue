<template>
  <div
    v-dialog="() => $emit('close')"
    class="modal open"
    @click.self="$emit('close')"
  >
    <div class="modal-card narrow">
      <div class="modal-head">
        <strong>调整头像</strong
        ><button
          class="icon-button"
          title="关闭"
          aria-label="关闭头像裁剪"
          @click="$emit('close')"
        >
          <X />
        </button>
      </div>
      <div class="avatar-crop-body">
        <div
          ref="viewport"
          class="avatar-crop-viewport"
          @pointerdown="start"
          @pointermove="move"
          @pointerup="stop"
          @pointercancel="stop"
        >
          <img
            ref="image"
            :src="url"
            alt="头像预览"
            draggable="false"
            :style="imageStyle"
            @load="ready"
            @error="error = '无法打开此图片，请重新选择'"
          />
          <div class="avatar-crop-mask"></div>
        </div>
        <label class="crop-zoom"
          >缩放<input
            v-model.number="zoom"
            aria-label="头像缩放"
            type="range"
            min="1"
            max="3"
            step="0.01"
        /></label>
        <p v-if="error" class="error-message">{{ error }}</p>
        <button class="primary" :disabled="!width" @click="crop">
          使用此头像
        </button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
const props = defineProps({ file: { type: File, required: true } })
const emit = defineEmits(['close', 'cropped'])
const url = URL.createObjectURL(props.file),
  image = ref(null),
  viewport = ref(null)
const width = ref(0),
  height = ref(0),
  zoom = ref(1),
  x = ref(0),
  y = ref(0),
  error = ref('')
const factor = computed(
  () => Math.max(240 / width.value, 240 / height.value) * zoom.value,
)
const imageStyle = computed(() =>
  width.value
    ? {
        width: `${width.value * factor.value}px`,
        height: `${height.value * factor.value}px`,
        transform: `translate(calc(-50% + ${x.value}px), calc(-50% + ${y.value}px))`,
      }
    : {},
)
function clamp() {
  const a = Math.max(0, (width.value * factor.value - 240) / 2),
    b = Math.max(0, (height.value * factor.value - 240) / 2)
  x.value = Math.max(-a, Math.min(a, x.value))
  y.value = Math.max(-b, Math.min(b, y.value))
}
function ready() {
  width.value = image.value.naturalWidth
  height.value = image.value.naturalHeight
}
let dragging = false,
  lastX,
  lastY
function start(e) {
  dragging = true
  lastX = e.clientX
  lastY = e.clientY
  viewport.value.setPointerCapture(e.pointerId)
}
function move(e) {
  if (!dragging) return
  x.value += e.clientX - lastX
  y.value += e.clientY - lastY
  lastX = e.clientX
  lastY = e.clientY
  clamp()
}
function stop() {
  dragging = false
}
function crop() {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 512
  const size = 240 / factor.value
  canvas
    .getContext('2d')
    .drawImage(
      image.value,
      (width.value - size) / 2 - x.value / factor.value,
      (height.value - size) / 2 - y.value / factor.value,
      size,
      size,
      0,
      0,
      512,
      512,
    )
  canvas.toBlob(
    (blob) => {
      if (blob)
        emit('cropped', new File([blob], 'avatar.jpg', { type: 'image/jpeg' }))
      else error.value = '生成头像失败，请重试'
    },
    'image/jpeg',
    0.9,
  )
}
watch(zoom, clamp)
onBeforeUnmount(() => URL.revokeObjectURL(url))
</script>
