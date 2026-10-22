<template>
  <div class="voice-recorder" :class="{ recording }">
    <div class="voice-head">
      <span class="voice-icon"><Mic :size="18" /></span>
      <div class="voice-copy">
        <strong>{{ recording ? '正在录音…' : file ? '语音已就绪' : '录一段声音' }}</strong>
        <small>{{
          recording
            ? `${clock(elapsed)} / 最多 ${maxMinutes} 分钟`
            : file
              ? `时长 ${clock(fileSeconds)}，可试听后发布`
              : '支持麦克风录制，也可直接上传音频文件'
        }}</small>
      </div>
      <button
        v-if="!recording && !file"
        class="primary voice-btn"
        type="button"
        :disabled="!supported"
        @click="start"
      >
        <Mic :size="16" />开始录制
      </button>
      <button
        v-if="recording"
        class="secondary voice-btn stop"
        type="button"
        @click="stop"
      >
        <Square :size="14" fill="currentColor" />停止
      </button>
    </div>

    <div v-if="recording" class="voice-live" aria-hidden="true">
      <span v-for="i in 22" :key="i" :style="{ animationDelay: `${i * 60}ms` }" />
    </div>

    <div v-if="file" class="voice-ready">
      <audio :src="fileUrl" controls preload="metadata" />
      <div class="voice-actions">
        <label class="text-button upload-replace">
          <FolderOpen :size="15" />换一个
          <input
            type="file"
            accept="audio/*"
            @change="onPick"
          />
        </label>
        <button class="text-button danger-text" type="button" @click="clear">
          <Trash2 :size="15" />移除语音
        </button>
      </div>
    </div>

    <label v-else-if="!recording" class="voice-upload">
      <Upload :size="15" />上传本地音频（MP3 / M4A / WAV / OGG）
      <input type="file" accept="audio/*" @change="onPick" />
    </label>

    <p v-if="error" class="voice-error" role="alert">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { FolderOpen, Mic, Square, Trash2, Upload } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: null },
  maxMinutes: { type: Number, default: 10 },
})
const emit = defineEmits(['update:modelValue'])

const supported =
  typeof navigator !== 'undefined' &&
  !!navigator.mediaDevices?.getUserMedia &&
  typeof MediaRecorder !== 'undefined'
const recording = ref(false)
const elapsed = ref(0)
const error = ref('')
const file = ref(props.modelValue)
const fileSeconds = ref(0)
const fileUrl = ref('')

let recorder = null
let stream = null
let chunks = []
let timer = null
let startedAt = 0

const maxSeconds = computed(() => props.maxMinutes * 60)

watch(
  () => props.modelValue,
  (v) => {
    if (v !== file.value) setFile(v)
  },
)

function revoke() {
  if (fileUrl.value) URL.revokeObjectURL(fileUrl.value)
  fileUrl.value = ''
}
function setFile(next) {
  revoke()
  file.value = next
  fileSeconds.value = 0
  if (next) fileUrl.value = URL.createObjectURL(next)
}
function clock(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
function emitFile(next) {
  setFile(next)
  emit('update:modelValue', next)
}
function pickMime() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ]
  return candidates.find((type) => MediaRecorder.isTypeSupported?.(type)) || ''
}
async function start() {
  error.value = ''
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    const mimeType = pickMime()
    recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    recorder.ondataavailable = (e) => {
      if (e.data?.size) chunks.push(e.data)
    }
    recorder.onstop = () => {
      const type = recorder?.mimeType || 'audio/webm'
      const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm'
      const blob = new Blob(chunks, { type })
      const voice = new File([blob], `voice-${Date.now()}.${ext}`, { type })
      if (voice.size > 20 * 1024 * 1024) {
        error.value = '语音不能超过 20 MB'
        clear()
        return
      }
      fileSeconds.value = Math.round((Date.now() - startedAt) / 1000)
      emitFile(voice)
    }
    startedAt = Date.now()
    recorder.start()
    recording.value = true
    elapsed.value = 0
    timer = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - startedAt) / 1000)
      if (elapsed.value >= maxSeconds.value) stop()
    }, 250)
  } catch (e) {
    error.value =
      e?.name === 'NotAllowedError'
        ? '没有麦克风权限，请在浏览器地址栏允许后重试'
        : '无法启动录音，可改用「上传本地音频」'
    recording.value = false
  }
}
function stop() {
  clearInterval(timer)
  recording.value = false
  try {
    recorder?.stop()
  } catch {
    /* ignore */
  }
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
  recorder = null
}
function onPick(event) {
  const picked = event.target.files?.[0]
  event.target.value = ''
  error.value = ''
  if (!picked) return
  if (!picked.type.startsWith('audio/')) {
    error.value = '请选择音频文件'
    return
  }
  if (picked.size > 20 * 1024 * 1024) {
    error.value = '语音不能超过 20 MB'
    return
  }
  fileSeconds.value = 0
  emitFile(picked)
}
function clear() {
  stop()
  revoke()
  file.value = null
  fileSeconds.value = 0
  emit('update:modelValue', null)
}
onBeforeUnmount(() => {
  clearInterval(timer)
  if (recording.value) stop()
  revoke()
})
</script>
