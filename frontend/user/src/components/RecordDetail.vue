<template>
  <Teleport to="body">
    <div class="record-backdrop" @click.self="close">
      <section ref="panel" class="record-dialog" aria-label="记录详情">
        <button
          class="icon-button record-close"
          title="关闭详情"
          aria-label="关闭详情"
          @click="close"
        >
          <X />
        </button>
        <div v-if="loading" class="record-loading skeleton">正在打开回忆…</div>
        <div v-else-if="error" class="record-loading">
          <p>{{ error }}</p>
          <button class="outline" @click="load">重试</button>
        </div>
        <template v-else-if="post">
          <div
            class="record-gallery"
            @touchstart.passive="touchStart"
            @touchend.passive="touchEnd"
          >
            <div ref="stage" class="record-stage">
              <template v-if="media?.kind === 'photo'">
                <img
                  v-if="media.preview_url"
                  class="record-blur-preview"
                  :src="media.preview_url"
                  alt=""
                />
                <img
                  v-if="!mediaError"
                  :key="media.id"
                  class="record-original"
                  :class="{ ready: originalReady }"
                  :src="media.original_url"
                  :alt="post.content || '记录照片'"
                  @load="originalReady = true"
                  @error="mediaError = true"
                />
                <span v-if="mediaError" class="gallery-status"
                  >原图暂不可用</span
                >
              </template>
              <video
                v-else-if="media?.kind === 'video' && !mediaError"
                ref="video"
                :key="media.id"
                :src="media.original_url"
                :poster="media.preview_url || undefined"
                controls
                playsinline
                preload="metadata"
                @error="mediaError = true"
              />
              <span v-else class="gallery-status">{{
                media ? '无法在线播放，请下载原文件' : '文字记录'
              }}</span>
              <template v-if="post.media.length > 1">
                <button
                  class="icon-button gallery-prev"
                  title="上一张"
                  aria-label="上一张"
                  :disabled="index === 0"
                  @click="change(-1)"
                >
                  <ChevronLeft />
                </button>
                <button
                  class="icon-button gallery-next"
                  title="下一张"
                  aria-label="下一张"
                  :disabled="index === post.media.length - 1"
                  @click="change(1)"
                >
                  <ChevronRight />
                </button>
              </template>
            </div>
            <div v-if="post.media.length" class="gallery-bottom">
              <span class="gallery-counter"
                >{{ index + 1 }} / {{ post.media.length }}</span
              >
              <div class="gallery-thumbs">
                <button
                  v-for="(m, i) in post.media"
                  :key="m.id"
                  :class="{ selected: i === index }"
                  :aria-label="`查看第 ${i + 1} 个媒体`"
                  @click="select(i)"
                >
                  <MediaPreview :media="m" />
                </button>
              </div>
              <a
                class="icon-button"
                :href="media.download_url"
                :title="media.kind === 'video' ? '下载原视频' : '导出原图'"
                :aria-label="media.kind === 'video' ? '下载原视频' : '导出原图'"
                ><Download
              /></a>
            </div>
          </div>
          <aside class="record-info">
            <div class="record-author">
              <UserAvatar
                :src="post.avatar"
                :name="post.nickname || post.username"
                class="av-coral"
              />
              <div>
                <strong>{{ post.nickname || post.username }}</strong
                ><small
                  >{{ post.event_date }}
                  <span v-if="post.activity_tag"
                    >· {{ post.activity_tag }}</span
                  ></small
                >
              </div>
            </div>
            <p v-if="post.circle_name" class="story-circle">
              <UsersRound :size="13" />{{ post.circle_name }}
            </p>
            <p v-if="!editing" class="record-content">
              {{ post.content || '这一刻，没有文字。' }}
            </p>
            <p v-if="post.location_name && !editing" class="muted">
              <MapPin :size="14" /> {{ post.location_name }}
            </p>
            <form v-if="editing" class="record-edit" @submit.prevent="saveEdit">
              <label
                >记录内容<textarea v-model="editForm.content"></textarea></label
              ><label
                >生活日期<input
                  type="date"
                  v-model="editForm.event_date"
                  required /></label
              ><label
                >标签<input
                  v-model="editForm.activity_tag"
                  maxlength="32" /></label
              ><label
                >主题分册<select
                  v-model="editForm.album_id"
                  aria-label="主题分册"
                >
                  <option :value="null">不加入分册</option>
                  <option v-for="a in albums" :key="a.id" :value="a.id">
                    {{ a.title }}
                  </option>
                </select></label
              ><label
                >时间线<select
                  v-model="editForm.line_id"
                  aria-label="时间线"
                  :disabled="!!selectedAlbumLine"
                >
                  <option :value="null">汇总主线</option>
                  <option v-for="line in lines" :key="line.id" :value="line.id">
                    {{ line.title }}
                  </option>
                </select></label
              ><FootprintMap picking v-model="editLocation" /><button
                class="primary"
                :disabled="busy"
              >
                {{ busy ? '保存中…' : '保存修改' }}</button
              ><button
                type="button"
                class="outline"
                :disabled="busy"
                @click="editing = false"
              >
                取消
              </button>
            </form>
            <button
              v-if="post.user_id === auth.user?.id && !editing"
              class="text-button"
              :disabled="busy"
              @click="startEdit"
            >
              <Pencil :size="16" />编辑记录
            </button>
            <div class="record-actions">
              <button
                class="icon-button"
                :class="{ liked: post.liked }"
                :title="post.liked ? '取消点赞' : '点赞'"
                :aria-label="post.liked ? '取消点赞' : '点赞'"
                :disabled="busy"
                @click="toggleLike"
              >
                <Heart
                  :size="18"
                  :fill="post.liked ? 'currentColor' : 'none'"
                /></button
              ><span class="like-count">{{ post.like_count }}</span>
              <button
                class="icon-button"
                title="收藏记录"
                aria-label="收藏记录"
                :disabled="busy"
                @click="favoriteOpen = true"
              >
                <Bookmark :size="18" />
              </button>
              <button class="text-button" @click="reportOpen = !reportOpen">
                <Flag :size="16" />举报</button
              ><button
                v-if="post.user_id === auth.user?.id || recordCircleManager"
                class="text-button danger-text"
                :disabled="busy"
                @click="remove"
              >
                <Trash2 :size="16" />删除记录
              </button>
            </div>
            <form
              v-if="reportOpen"
              class="report-form"
              @submit.prevent="report"
            >
              <label for="report-type">举报类型</label
              ><select id="report-type" v-model="reportType">
                <option v-for="type in reportTypes" :key="type">
                  {{ type }}
                </option>
              </select>
              <textarea
                v-model="reason"
                aria-label="举报说明"
                placeholder="举报说明"
                maxlength="1000"
                :required="reportType === '其他'"
              ></textarea>
              <button class="primary" :disabled="busy">
                {{ busy ? '提交中…' : '提交举报' }}
              </button>
            </form>
            <div class="record-comments">
              <h3>
                评论 <span>{{ post.comments.length }}</span>
              </h3>
              <p v-if="!post.comments.length" class="muted">还没有评论。</p>
              <div
                v-for="c in post.comments"
                :key="c.id"
                class="detail-comment"
              >
                <strong>{{ c.nickname || c.username }}</strong>
                <p>
                  <span v-if="c.reply_to_name" class="reply-to"
                    >回复 {{ c.reply_to_name }}：</span
                  >{{ c.content }}
                </p>
                <button class="text-button" :disabled="busy" @click="reply(c)">
                  回复
                </button>
                <button
                  v-if="c.user_id === auth.user?.id || recordCircleManager"
                  class="text-button"
                  :disabled="busy"
                  @click="removeComment(c.id)"
                >
                  删除
                </button>
              </div>
            </div>
            <div v-if="replyTarget" class="reply-context">
              <span
                >回复 {{ replyTarget.nickname || replyTarget.username }}</span
              ><button
                class="icon-button"
                title="取消回复"
                aria-label="取消回复"
                @click="replyTarget = null"
              >
                <X :size="15" />
              </button>
            </div>
            <form class="comment-compose" @submit.prevent="comment">
              <input
                ref="commentInput"
                v-model="commentText"
                aria-label="评论内容"
                placeholder="写一句…"
                maxlength="500"
              /><button
                class="icon-button"
                title="发送评论"
                aria-label="发送评论"
                :disabled="busy || !commentText.trim()"
              >
                <Send :size="19" />
              </button>
            </form>
            <p v-if="actionError" class="error-message" role="alert">
              {{ actionError }}
            </p>
          </aside>
        </template>
      </section>
      <FavoritePicker
        v-if="favoriteOpen && post"
        :post-id="post.id"
        @close="favoriteOpen = false"
        @saved="toast('收藏已保存')"
      />
    </div>
  </Teleport>
</template>
<script setup>
import {
  computed,
  inject,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Bookmark,
  Heart,
  Flag,
  MapPin,
  Pencil,
  Send,
  Trash2,
  UsersRound,
  X,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { activateDialog } from '../utils/dialog'
import { confirmDialog } from '../utils/confirm'
import MediaPreview from './MediaPreview.vue'
import FootprintMap from './FootprintMap.vue'
import UserAvatar from './UserAvatar.vue'
import FavoritePicker from './FavoritePicker.vue'
const props = defineProps({ request: { type: Object, required: true } })
const emit = defineEmits(['close', 'changed'])
const auth = useAuthStore()
const toast = inject('toast')
const post = ref(null),
  loading = ref(true),
  error = ref(''),
  actionError = ref(''),
  busy = ref(false)
const panel = ref(null),
  stage = ref(null),
  video = ref(null),
  commentInput = ref(null)
const index = ref(0),
  originalReady = ref(false),
  mediaError = ref(false)
const commentText = ref(''),
  reportOpen = ref(false),
  reason = ref(''),
  reportType = ref('骚扰辱骂')
const reportTypes = ['骚扰辱骂', '隐私侵权', '广告引流', '其他']
const media = computed(() => post.value?.media[index.value])
const recordCircleManager = computed(
  () =>
    !!auth.circles.find((circle) => circle.id === post.value?.circle_id)
      ?.can_manage,
)
const favoriteOpen = ref(false),
  replyTarget = ref(null)
const editing = ref(false),
  lines = ref([]),
  albums = ref([]),
  editLocation = ref(null)
const editForm = reactive({
  content: '',
  event_date: '',
  activity_tag: '',
  album_id: null,
  line_id: null,
})
const selectedAlbumLine = computed(
  () => albums.value.find((a) => a.id === editForm.album_id)?.line_id,
)
watch(selectedAlbumLine, (id) => {
  if (id) editForm.line_id = id
})
let release,
  touchX = 0,
  touchY = 0,
  alive = true,
  closing = false
const reduced = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get(`/api/posts/${props.request.id}`)
    if (!alive) return
    post.value = data
    index.value = Math.max(
      0,
      data.media.findIndex((m) => m.id === props.request.mediaId),
    )
  } catch (e) {
    if (alive) error.value = e.userMessage || '记录已删除或无法访问'
  } finally {
    if (alive) loading.value = false
  }
  await nextTick()
  if (!alive) return
  animate(false)
  if (props.request.comments) commentInput.value?.focus()
}
function animate(reverse) {
  const source = props.request.source
  if (
    reduced() ||
    !stage.value ||
    !source?.isConnected ||
    index.value !==
      Math.max(
        0,
        post.value.media.findIndex((m) => m.id === props.request.mediaId),
      )
  )
    return null
  const a = source.getBoundingClientRect(),
    b = stage.value.getBoundingClientRect()
  if (!a.width || a.bottom < 0 || a.top > innerHeight) return null
  const frames = [
    {
      transform: `translate(${a.left - b.left}px, ${a.top - b.top}px) scale(${a.width / b.width}, ${a.height / b.height})`,
      opacity: 0.6,
    },
    { transform: 'none', opacity: 1 },
  ]
  return stage.value.animate(reverse ? frames.reverse() : frames, {
    duration: 280,
    easing: 'cubic-bezier(.22,1,.36,1)',
  })
}
async function close() {
  if (closing) return
  if (busy.value) return
  if (
    editing.value &&
    !(await confirmDialog({
      title: '放弃修改',
      message: '尚未保存的修改将丢失。',
      confirmText: '放弃修改',
    }))
  )
    return
  closing = true
  video.value?.pause()
  const animation = post.value && animate(true)
  if (animation) await animation.finished.catch(() => {})
  emit('close')
}
function select(i) {
  video.value?.pause()
  index.value = i
  originalReady.value = false
  mediaError.value = false
}
function change(delta) {
  if (post.value)
    select(
      Math.max(0, Math.min(post.value.media.length - 1, index.value + delta)),
    )
}
function keydown(e) {
  if (
    document.querySelector('.confirm-card') ||
    /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)
  )
    return
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    e.preventDefault()
    change(e.key === 'ArrowLeft' ? -1 : 1)
  }
}
function touchStart(e) {
  touchX = e.changedTouches[0].clientX
  touchY = e.changedTouches[0].clientY
}
function touchEnd(e) {
  const dx = e.changedTouches[0].clientX - touchX,
    dy = e.changedTouches[0].clientY - touchY
  if (
    media.value?.kind !== 'video' &&
    Math.abs(dx) > 60 &&
    Math.abs(dx) > Math.abs(dy) * 1.5
  )
    change(dx < 0 ? 1 : -1)
}
async function action(fn) {
  if (busy.value) return
  busy.value = true
  actionError.value = ''
  try {
    await fn()
  } catch (e) {
    actionError.value = e.userMessage || '操作失败，请重试'
  } finally {
    busy.value = false
  }
}
function comment() {
  if (!commentText.value.trim()) return
  action(async () => {
    const { data } = await api.post(`/api/posts/${post.value.id}/comments`, {
      content: commentText.value.trim(),
      reply_to_id: replyTarget.value?.id,
    })
    post.value.comments.push(data)
    commentText.value = ''
    replyTarget.value = null
    emit('changed')
    await nextTick()
    commentInput.value?.focus()
  })
}
function reply(c) {
  replyTarget.value = c
  nextTick(() => commentInput.value?.focus())
}
function toggleLike() {
  action(async () => {
    const response = post.value.liked
      ? await api.delete(`/api/posts/${post.value.id}/like`)
      : await api.put(`/api/posts/${post.value.id}/like`)
    post.value.liked = response.data.liked
    post.value.like_count = response.data.like_count
    emit('changed')
  })
}
async function removeComment(id) {
  if (
    !(await confirmDialog({
      title: '删除评论',
      message: '删除后无法恢复。',
      danger: true,
    }))
  )
    return
  action(async () => {
    await api.delete(`/api/comments/${id}`)
    post.value.comments = post.value.comments.filter((c) => c.id !== id)
    emit('changed')
  })
}
function report() {
  action(async () => {
    await api.post(`/api/posts/${post.value.id}/reports`, {
      report_type: reportType.value,
      reason: reason.value.trim(),
    })
    reportOpen.value = false
    emit('changed')
    toast('举报已提交，等待审核')
  })
}
async function startEdit() {
  action(async () => {
    const [l, a] = await Promise.all([
      api.get(`/api/circles/${post.value.circle_id}/lines`),
      api.get(`/api/circles/${post.value.circle_id}/albums`),
    ])
    lines.value = l.data
    albums.value = a.data
    Object.assign(editForm, {
      content: post.value.content,
      event_date: post.value.event_date,
      activity_tag: post.value.activity_tag || '',
      album_id: post.value.album_id,
      line_id: post.value.line_id,
    })
    editLocation.value =
      post.value.latitude == null
        ? null
        : {
            latitude: post.value.latitude,
            longitude: post.value.longitude,
            location_name: post.value.location_name,
          }
    editing.value = true
  })
}
function saveEdit() {
  action(async () => {
    const { data } = await api.patch(`/api/posts/${post.value.id}`, {
      ...editForm,
      album_id: editForm.album_id || 0,
      latitude: editLocation.value?.latitude ?? null,
      longitude: editLocation.value?.longitude ?? null,
      location_name: editLocation.value?.location_name ?? null,
    })
    post.value = data
    editing.value = false
    emit('changed')
    toast('记录已更新')
  })
}
async function remove() {
  if (
    !(await confirmDialog({
      title: '删除记录',
      message: '将删除记录及其全部原文件，不可恢复。',
      confirmText: '删除记录',
      danger: true,
    }))
  )
    return
  action(async () => {
    await api.delete(`/api/posts/${post.value.id}`)
    emit('changed')
    toast('记录已删除')
    emit('close')
  })
}
onMounted(() => {
  release = activateDialog(panel.value, close)
  window.addEventListener('keydown', keydown)
  load()
})
onBeforeUnmount(() => {
  alive = false
  video.value?.pause()
  release?.()
  window.removeEventListener('keydown', keydown)
})
watch(
  () => auth.currentCircleId,
  () => emit('close'),
)
</script>
