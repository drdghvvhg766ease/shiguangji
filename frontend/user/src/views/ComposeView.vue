<template>
  <section aria-label="发布记录">
    <div class="page-head">
      <div>
        <span class="eyebrow">留下今天，或者补记从前</span>
        <h1>记录这一刻</h1>
        <p>保存一段日子，也让朋友一起看见</p>
      </div>
    </div>

    <form class="compose-form" id="preview-form" @submit.prevent="submit">
      <fieldset :disabled="submitting" class="compose-fields">
        <div class="form-group">
          <label for="photo-input">照片</label>
          <div class="upload-zone" @dragover.prevent @drop.prevent="onDrop">
            <div>
              <ImagePlus class="icon" />
              <strong>选择照片或拖到这里</strong>
              <small
                >支持多张照片，最多 9 张；也可选一段短视频（MP4/MOV）</small
              >
            </div>
            <input
              id="photo-input"
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
              multiple
              aria-label="选择照片"
              @change="onFiles"
            />
          </div>
          <div class="upload-preview" id="upload-preview">
            <div v-for="(p, i) in previews" :key="p.url" class="upload-item">
              <img :src="p.url" :alt="p.name" decoding="async" /><small>{{
                p.name
              }}</small>
              <div class="upload-item-actions">
                <button
                  class="icon-button"
                  type="button"
                  title="前移"
                  aria-label="前移照片"
                  :disabled="i === 0"
                  @click="move(i, -1)"
                >
                  <ArrowLeft /></button
                ><button
                  class="icon-button"
                  type="button"
                  title="后移"
                  aria-label="后移照片"
                  :disabled="i === previews.length - 1"
                  @click="move(i, 1)"
                >
                  <ArrowRight /></button
                ><button
                  class="icon-button"
                  type="button"
                  title="移除"
                  aria-label="移除照片"
                  @click="removeFile(i)"
                >
                  <X />
                </button>
              </div>
            </div>
          </div>
          <p v-if="videoName" class="eyebrow" style="margin-top: 8px">
            视频：{{ videoName }}
            <button type="button" class="text-button" @click="removeVideo">
              移除
            </button>
          </p>
        </div>

        <div class="form-group">
          <label for="memory-text">这一天想说什么</label>
          <textarea
            id="memory-text"
            v-model="content"
            placeholder="写下当时的小事、心情或一句话……"
          ></textarea>
        </div>

        <div class="form-split">
          <div class="form-group">
            <label for="memory-date">生活日期</label>
            <input id="memory-date" type="date" v-model="eventDate" required />
          </div>
          <div class="form-group">
            <label for="memory-tag">活动标签</label>
            <select id="memory-tag" v-model="activityTag">
              <option value="毕业">毕业</option>
              <option value="旅行">旅行</option>
              <option value="聚餐">聚餐</option>
              <option value="日常">日常</option>
              <option value="节日">节日</option>
              <option value="运动">运动</option>
              <option value="学习">学习</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="memory-album">加入主题分册</label>
          <select id="memory-album" v-model="albumId">
            <option :value="null">不加入分册</option>
            <option v-for="a in albums" :key="a.id" :value="a.id">
              {{ a.title }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label for="memory-line">时间线</label
          ><select id="memory-line" v-model="lineId" :disabled="!!albumLine">
            <option :value="null">汇总主线</option>
            <option v-for="line in lines" :key="line.id" :value="line.id">
              {{ line.title }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <button
            class="text-button"
            type="button"
            @click="showLocation = !showLocation"
          >
            <MapPin :size="17" />{{
              location ? location.location_name : '添加旅行地点'
            }}</button
          ><FootprintMap v-if="showLocation" picking v-model="location" />
        </div>

        <div class="form-actions">
          <button class="outline" type="button" @click="$emit('nav', 'feed')">
            取消
          </button>
          <button class="primary" type="submit" :disabled="submitting">
            <Send class="icon" />
            {{ submitting ? '发布中…' : '发布记录' }}
          </button>
        </div>
      </fieldset>
      <div v-if="submitting" class="upload-progress" role="status">
        <span>{{ progress < 100 ? '正在上传' : '正在保存记录' }}</span
        ><span>{{ progress }}%</span
        ><progress :value="progress" max="100"></progress>
      </div>
      <p
        v-if="error"
        style="color: var(--terracotta-dark); font-size: 12px; margin-top: 12px"
      >
        {{ error }}
      </p>
    </form>
  </section>
</template>

<script setup>
import {
  computed,
  inject,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
  watch,
} from 'vue'
import {
  ArrowLeft,
  ArrowRight,
  ImagePlus,
  MapPin,
  Send,
  X,
} from 'lucide-vue-next'
import { confirmDialog } from '../utils/confirm'
import FootprintMap from '../components/FootprintMap.vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['nav', 'published'])
const props = defineProps({
  presetAlbumId: { type: [Number, null], default: null },
})
const auth = useAuthStore()
const toast = inject('toast')

const kind = ref('photo')
const photoFiles = ref([])
const previews = ref([])
const videoFile = ref(null)
const videoName = ref('')
const content = ref('')
const eventDate = ref(new Date().toISOString().slice(0, 10))
const activityTag = ref('日常')
const albumId = ref(props.presetAlbumId)
const albums = ref([])
const lines = ref([]),
  lineId = ref(null),
  location = ref(null),
  showLocation = ref(false)
const albumLine = computed(
  () => albums.value.find((a) => a.id === albumId.value)?.line_id,
)
watch(albumLine, (id) => {
  if (id) lineId.value = id
})
const submitting = ref(false)
const error = ref('')
const progress = ref(0)
const draftGuard = inject('draftGuard')
const initialDate = new Intl.DateTimeFormat('sv-SE').format(new Date())
const initialLine = computed(
  () => albums.value.find((a) => a.id === props.presetAlbumId)?.line_id || null,
)
eventDate.value = initialDate
const dirty = computed(
  () =>
    content.value.trim() ||
    photoFiles.value.length ||
    videoFile.value ||
    location.value ||
    lineId.value !== initialLine.value ||
    albumId.value !== props.presetAlbumId ||
    eventDate.value !== initialDate ||
    activityTag.value !== '日常',
)
let albumSequence = 0
async function leave() {
  if (submitting.value) {
    toast('记录正在保存，请稍候')
    return false
  }
  if (!dirty.value) return true
  const ok = await confirmDialog({
    title: '离开发布页面',
    message: '尚未发布的内容将被丢弃。',
    confirmText: '丢弃草稿',
  })
  if (ok) reset()
  return ok
}
function reset() {
  previews.value.forEach((p) => URL.revokeObjectURL(p.url))
  previews.value = []
  photoFiles.value = []
  videoFile.value = null
  videoName.value = ''
  content.value = ''
  eventDate.value = initialDate
  activityTag.value = '日常'
  albumId.value = props.presetAlbumId
  lineId.value = initialLine.value
  location.value = null
  showLocation.value = false
  error.value = ''
}
function beforeUnload(e) {
  if (dirty.value || submitting.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}
onActivated(() => {
  draftGuard.value = leave
  window.addEventListener('beforeunload', beforeUnload)
})
onDeactivated(() => {
  if (draftGuard.value === leave) draftGuard.value = null
  window.removeEventListener('beforeunload', beforeUnload)
})
function removeFile(i) {
  URL.revokeObjectURL(previews.value[i].url)
  previews.value.splice(i, 1)
  photoFiles.value.splice(i, 1)
}
function removeVideo() {
  videoFile.value = null
  videoName.value = ''
}
function move(i, d) {
  const target = i + d
  ;[photoFiles.value[i], photoFiles.value[target]] = [
    photoFiles.value[target],
    photoFiles.value[i],
  ]
  ;[previews.value[i], previews.value[target]] = [
    previews.value[target],
    previews.value[i],
  ]
}

watch(
  () => props.presetAlbumId,
  (v) => {
    albumId.value = v
  },
)

function onFiles(e) {
  if (submitting.value) return
  const files = [...e.target.files]
  e.target.value = ''
  if (!files.length) return
  const photos = ['image/jpeg', 'image/png', 'image/webp'],
    videos = ['video/mp4', 'video/quicktime']
  if (files.some((f) => !photos.includes(f.type) && !videos.includes(f.type))) {
    error.value = '仅支持 JPEG、PNG、WebP、MP4 和 MOV'
    return
  }
  if (
    files.some((f) => videos.includes(f.type)) &&
    (files.length !== 1 || photoFiles.value.length)
  ) {
    error.value = '每条记录只能选择一段视频，不能与照片混合'
    return
  }
  if (files.some((f) => photos.includes(f.type)) && videoFile.value) {
    error.value = '请先移除已选择的视频'
    return
  }
  if (files.some((f) => photos.includes(f.type) && f.size > 10 * 1024 * 1024)) {
    error.value = '单张照片不能超过 10MB'
    return
  }
  if (
    photoFiles.value.length + files.length > 9 &&
    files.every((f) => photos.includes(f.type))
  ) {
    error.value = '每条最多 9 张照片，请先移除部分照片'
    return
  }
  if (files[0].type.startsWith('video/')) {
    if (files[0].size > 100 * 1024 * 1024) {
      error.value = '视频不能超过 100MB'
      return
    }
    kind.value = 'video'
    videoFile.value = files[0]
    videoName.value = files[0].name
    photoFiles.value = []
    previews.value.forEach((p) => URL.revokeObjectURL(p.url))
    previews.value = []
    error.value = ''
    return
  }
  kind.value = 'photo'
  videoFile.value = null
  videoName.value = ''
  const incoming = files.filter((f) => f.type.startsWith('image/'))
  const merged = [...photoFiles.value, ...incoming]
  photoFiles.value = merged
  previews.value.forEach((p) => URL.revokeObjectURL(p.url))
  previews.value = merged.map((f) => ({
    name: f.name,
    url: URL.createObjectURL(f),
  }))
  error.value = ''
}

function onDrop(e) {
  onFiles({ target: { files: e.dataTransfer.files, value: '' } })
}

async function submit() {
  if (submitting.value) return
  error.value = ''
  if (kind.value === 'photo' && !photoFiles.value.length) {
    error.value = '请选择至少一张照片'
    return
  }
  if (kind.value === 'video' && !videoFile.value) {
    error.value = '请选择一段视频'
    return
  }
  submitting.value = true
  progress.value = 0
  try {
    const fd = new FormData()
    fd.append('content', content.value)
    fd.append('event_date', eventDate.value)
    if (activityTag.value) fd.append('activity_tag', activityTag.value)
    if (albumId.value != null) fd.append('album_id', String(albumId.value))
    if (lineId.value != null) fd.append('line_id', String(lineId.value))
    if (location.value) {
      fd.append('latitude', String(location.value.latitude))
      fd.append('longitude', String(location.value.longitude))
      fd.append('location_name', location.value.location_name)
    }
    if (kind.value === 'photo') {
      for (const f of photoFiles.value) fd.append('files', f)
    } else {
      fd.append('files', videoFile.value)
    }
    await api.post(`/api/circles/${auth.currentCircleId}/posts`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total)
          progress.value = Math.min(100, Math.round((e.loaded / e.total) * 100))
      },
    })
    toast('发布成功，已存下这一刻')
    const target = albumId.value
    reset()
    submitting.value = false
    emit('published', target)
  } catch (e) {
    error.value = e.userMessage || '发布失败'
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(() => {
  if (draftGuard.value === leave) draftGuard.value = null
  window.removeEventListener('beforeunload', beforeUnload)
  previews.value.forEach((p) => URL.revokeObjectURL(p.url))
})

async function loadOptions() {
  const sequence = ++albumSequence,
    circle = auth.currentCircleId
  if (!circle) return
  try {
    const [a, l] = await Promise.all([
      api.get(`/api/circles/${circle}/albums`),
      api.get(`/api/circles/${circle}/lines`),
    ])
    if (sequence !== albumSequence || circle !== auth.currentCircleId) return
    albums.value = a.data
    lines.value = l.data
  } catch {
    /* optional */
  }
}
onActivated(loadOptions)
watch(
  () => auth.currentCircleId,
  async () => {
    const sequence = ++albumSequence,
      circle = auth.currentCircleId
    albums.value = []
    if (!auth.currentCircleId) return
    try {
      const [a, l] = await Promise.all([
        api.get(`/api/circles/${circle}/albums`),
        api.get(`/api/circles/${circle}/lines`),
      ])
      if (sequence === albumSequence && circle === auth.currentCircleId) {
        albums.value = a.data
        lines.value = l.data
      }
    } catch (e) {
      error.value = e.userMessage || '分册加载失败'
    }
  },
)
</script>
