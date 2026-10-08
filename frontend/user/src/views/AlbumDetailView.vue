<template>
  <section aria-label="主题分册">
    <div v-if="loading" class="feed-skeleton" aria-label="正在加载">
      <div class="skeleton"></div>
    </div>
    <div v-else-if="error" class="empty-state">
      <p>{{ error }}</p>
      <button class="outline" @click="load">重试</button
      ><button class="text-button" @click="$emit('back')">返回相册</button>
    </div>
    <template v-else-if="album">
      <div class="page-head">
        <div>
          <span class="eyebrow">共同相册 / 主题分册</span>
          <h1 id="album-title-top">{{ album.title }}</h1>
          <p id="album-created-by">
            由 {{ creatorName }} 创建 · {{ formatDay(album.created_at) }}
          </p>
        </div>
        <button class="outline" type="button" @click="$emit('back')">
          <ArrowLeft class="icon" />
          返回相册
        </button>
      </div>

      <div
        v-if="auth.canManage || album.created_by === auth.user?.id"
        class="line-toolbar"
      >
        <div>
          <button class="text-button" @click="openManage">
            <Pencil :size="16" />编辑分册</button
          ><button
            class="text-button danger-text"
            :disabled="managing"
            @click="deleteAlbum"
          >
            <Trash2 :size="16" />删除分册
          </button>
        </div>
        <span class="eyebrow">{{
          lines.find((l) => l.id === album.line_id)?.title || '汇总主线'
        }}</span>
      </div>
      <div class="album-detail-cover" :class="coverClass">
        <img
          v-for="(id, i) in (album.cover_thumbs || []).slice(0, 4)"
          :key="id"
          :src="`/api/media/${id}/file?variant=preview`"
          alt=""
          loading="lazy"
          decoding="async"
        />
        <div
          v-if="!(album.cover_thumbs || []).length"
          style="
            grid-column: 1 / -1;
            display: grid;
            place-items: center;
            color: var(--pine);
            font-family: 'Noto Serif SC', serif;
            font-size: 18px;
          "
        >
          还没有封面照片
        </div>
      </div>

      <div class="album-detail-copy">
        <div>
          <span class="eyebrow">我们的主题分册</span>
          <h1 id="album-title-main">{{ album.title }}</h1>
          <p id="album-stats">
            {{ album.post_count }} 条记录 · {{ photoCount }} 张照片 ·
            {{ album.participant_count }} 位成员参与
          </p>
        </div>
        <div class="album-detail-actions">
          <button
            class="secondary"
            type="button"
            @click="$emit('compose', album.id)"
          >
            <Plus class="icon" />
            加入接力
          </button>
          <button
            class="outline"
            type="button"
            id="guess-open"
            @click="startGuess"
          >
            <Sparkles class="icon" />
            猜猜那天
          </button>
        </div>
      </div>

      <div class="relay-band">
        <div>
          <strong>接力题目</strong>
          <p id="album-prompt">
            {{ album.prompt || '随手拍下最想记住的一张。' }}
          </p>
        </div>
        <div class="participant" id="album-participants">
          <span
            v-for="p in album.participants || []"
            :key="p.user_id"
            class="avatar av-coral"
            :class="avatarClass(p.user_id)"
          >
            {{ (p.nickname || '?').slice(0, 1) }}
          </span>
          <span>{{ album.participant_count }} 位朋友已加入</span>
        </div>
      </div>

      <div class="section-head">
        <h2>大家的照片</h2>
        <button
          class="text-button"
          type="button"
          @click="$emit('compose', album.id)"
        >
          我也来记录
          <ArrowRight class="icon" />
        </button>
      </div>

      <div class="album-grid" id="album-detail-grid">
        <button
          v-for="p in posts"
          :key="p.id"
          type="button"
          :aria-label="`打开记录：${p.content}`"
          @click="openFromPost(p, $event)"
        >
          <MediaPreview
            v-if="p.media[0]"
            :media="p.media[0]"
            :alt="p.content"
          />
        </button>
      </div>
      <div v-if="!posts.length" class="empty-state" id="album-detail-empty">
        还没有照片，加入接力留下第一张吧。
      </div>

      <div
        v-if="manageOpen"
        v-dialog="() => (manageOpen = false)"
        class="modal open"
        @click.self="manageOpen = false"
      >
        <form class="modal-card narrow" @submit.prevent="saveAlbum">
          <div class="modal-head">
            <strong>编辑分册</strong
            ><button
              class="icon-button"
              type="button"
              title="关闭"
              aria-label="关闭"
              @click="manageOpen = false"
            >
              <X />
            </button>
          </div>
          <div class="line-form">
            <label
              >标题<input
                v-model="manageForm.title"
                maxlength="64"
                required /></label
            ><label
              >接力题目<input
                v-model="manageForm.prompt"
                maxlength="200" /></label
            ><label
              >归属时间线<select v-model="manageForm.line_id">
                <option :value="null">汇总主线</option>
                <option v-for="l in lines" :key="l.id" :value="l.id">
                  {{ l.title }}
                </option>
              </select></label
            >
            <p v-if="manageError" class="error-message">{{ manageError }}</p>
            <button class="primary" :disabled="managing">
              {{ managing ? '保存中…' : '保存分册' }}
            </button>
          </div>
        </form>
      </div>
      <!-- 猜猜那天 -->
      <div
        v-if="guessOpen"
        v-dialog="() => (guessOpen = false)"
        class="modal open"
        @click.self="guessOpen = false"
      >
        <div class="modal-card">
          <div class="modal-head">
            <strong>猜猜那天</strong>
            <button
              class="more"
              type="button"
              id="guess-close"
              @click="guessOpen = false"
            >
              <X class="icon" />
            </button>
          </div>
          <img
            v-if="currentGuess"
            class="modal-photo"
            id="guess-photo"
            :src="currentGuess?.preview_url"
            alt="等待揭晓的回忆照片"
          />
          <div class="modal-info">
            <div>
              <h2 id="guess-title">
                {{ revealed ? '那天的答案' : '这张照片是哪一天？' }}
              </h2>
              <p id="guess-caption">
                <template v-if="revealed && currentGuess">
                  {{ currentGuess.author_nickname }} ·
                  {{ formatDay(currentGuess.event_date) }} ·
                  {{ currentGuess.content || '无文字' }}
                </template>
                <template v-else>{{
                  currentGuess
                    ? '猜猜是谁拍的，再点揭晓答案。'
                    : '分册还没有可用照片，加入接力留下第一张吧。'
                }}</template>
              </p>
            </div>
            <div class="modal-actions">
              <button
                class="outline"
                type="button"
                id="guess-reveal"
                :disabled="!currentGuess || revealed"
                @click="revealed = true"
              >
                揭晓答案
              </button>
              <button
                class="secondary"
                type="button"
                id="guess-next"
                :disabled="guessPool.length < 2"
                @click="nextGuess"
              >
                下一张
                <ArrowRight class="icon" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import {
  computed,
  inject,
  onActivated,
  onDeactivated,
  reactive,
  ref,
  watch,
} from 'vue'
import MediaPreview from '../components/MediaPreview.vue'
import {
  ArrowLeft,
  ArrowRight,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { confirmDialog } from '../utils/confirm'

const props = defineProps({
  albumId: { type: [Number, null], default: null },
})
const emit = defineEmits(['back', 'compose', 'open-post'])
const auth = useAuthStore()
const toast = inject('toast')

const album = ref(null)
const posts = ref([])
const guessOpen = ref(false)
const guessPool = ref([])
const drawn = ref([])
const revealed = ref(false)
const lines = ref([]),
  manageOpen = ref(false),
  managing = ref(false),
  manageError = ref('')
const manageForm = reactive({ title: '', prompt: '', line_id: null })
const loading = ref(true),
  error = ref(''),
  revision = inject('revision')
let sequence = 0,
  loadedRevision = -1,
  active = false

const creatorName = computed(() => {
  const p = (album.value?.participants || []).find(
    (x) => x.user_id === album.value?.created_by,
  )
  return p ? p.nickname || p.username : '朋友'
})

const photoCount = computed(() =>
  posts.value.reduce((s, p) => s + p.media.length, 0),
)
const coverClass = computed(() => {
  const n = album.value?.cover_thumbs?.length || 0
  return { empty: n === 0, single: n === 1 }
})

const currentGuess = computed(() => {
  const left = guessPool.value.filter((g) => !drawn.value.includes(g.media_id))
  return left[0] || guessPool.value[0] || null
})

function avatarClass(id) {
  return ['av-coral', 'av-teal', 'av-gold', 'av-green'][Number(id || 0) % 4]
}

function formatDay(s) {
  const d = String(s).slice(0, 10)
  const [, m, day] = d.split('-')
  return `${Number(m)} 月 ${Number(day)} 日`
}

function openFromPost(p, event) {
  emit('open-post', {
    id: p.id,
    mediaId: p.media[0]?.id,
    source: event.currentTarget.querySelector('img'),
  })
}

async function load() {
  const seq = ++sequence,
    circle = auth.currentCircleId,
    id = props.albumId
  if (!circle || !id) {
    loading.value = false
    return
  }
  loading.value = !album.value
  error.value = ''
  try {
    const [aRes, pRes, lRes] = await Promise.all([
      api.get(`/api/circles/${circle}/albums/${id}`),
      api.get(`/api/circles/${circle}/posts`, { params: { album_id: id } }),
      api.get(`/api/circles/${circle}/lines`),
    ])
    if (
      seq !== sequence ||
      circle !== auth.currentCircleId ||
      id !== props.albumId
    )
      return
    album.value = aRes.data
    posts.value = pRes.data
    lines.value = lRes.data
    loadedRevision = revision.value
  } catch (e) {
    if (seq === sequence) error.value = e.userMessage || '加载分册失败'
  } finally {
    if (seq === sequence) loading.value = false
  }
}

async function startGuess() {
  const circle = auth.currentCircleId,
    id = props.albumId
  try {
    const { data } = await api.get(`/api/circles/${circle}/albums/${id}/guess`)
    if (circle !== auth.currentCircleId || id !== props.albumId || !active)
      return
    if (data.length < 2) toast('分册照片少于两张，请继续投稿')
    guessPool.value = data
    drawn.value = []
    revealed.value = false
    guessOpen.value = true
  } catch (e) {
    toast(e.userMessage || '加载猜照片失败')
  }
}

function nextGuess() {
  if (currentGuess.value) drawn.value.push(currentGuess.value.media_id)
  revealed.value = false
  const left = guessPool.value.filter((g) => !drawn.value.includes(g.media_id))
  if (!left.length) drawn.value = []
}

onActivated(() => {
  active = true
  if (loadedRevision !== revision.value) load()
})
onDeactivated(() => {
  active = false
  guessOpen.value = false
  manageOpen.value = false
})
watch(revision, () => {
  if (active) load()
})
function openManage() {
  Object.assign(manageForm, {
    title: album.value.title,
    prompt: album.value.prompt || '',
    line_id: album.value.line_id,
  })
  manageError.value = ''
  manageOpen.value = true
}
async function saveAlbum() {
  if (managing.value) return
  managing.value = true
  manageError.value = ''
  try {
    await api.patch(
      `/api/circles/${auth.currentCircleId}/albums/${props.albumId}`,
      manageForm,
    )
    manageOpen.value = false
    revision.value++
    toast('分册已更新')
  } catch (e) {
    manageError.value = e.userMessage || '保存失败'
  } finally {
    managing.value = false
  }
}
async function deleteAlbum() {
  if (
    managing.value ||
    !(await confirmDialog({
      title: '删除分册',
      message: '只删除分册，记录和照片仍保留在朋友圈。',
      confirmText: '删除分册',
      danger: true,
    }))
  )
    return
  managing.value = true
  try {
    await api.delete(
      `/api/circles/${auth.currentCircleId}/albums/${props.albumId}`,
    )
    emit('back')
    revision.value++
    toast('分册已删除')
  } catch (e) {
    toast(e.userMessage || '删除失败')
  } finally {
    managing.value = false
  }
}
</script>
