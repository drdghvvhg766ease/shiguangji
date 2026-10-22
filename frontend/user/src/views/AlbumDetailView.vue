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
          <div class="guess-headline">
            <span class="guess-score">我的积分 <strong>{{ myScore }}</strong></span>
            <span v-if="!guessResult" class="guess-timer" :class="{ urgent: timerLeft <= 5 }">
              倒计时 {{ timerLeft }}s
            </span>
            <span v-else class="guess-timer done">已作答</span>
          </div>
          <img
            v-if="currentGuess"
            class="modal-photo"
            id="guess-photo"
            :src="currentGuess.preview_url"
            alt="等待揭晓的回忆照片"
          />
          <div class="modal-info guess-info">
            <div>
              <h2 id="guess-title">
                {{ guessResult ? '那天的答案' : '这张照片拍在哪个月？' }}
              </h2>
              <p id="guess-caption">
                <template v-if="guessResult">
                  {{ guessResult.correct ? '猜对了！' : '差一点。' }}
                  实际是 {{ guessResult.actual_label }}（{{ formatDay(guessResult.event_date) }}），
                  由 {{ guessResult.author }} 拍下。
                  <span class="guess-points">+{{ guessResult.points }} 分</span>
                </template>
                <template v-else-if="currentGuess">
                  {{ usedHint ? `提示：${hintText}` : '凭直觉选一个月份，快答有加分。' }}
                </template>
                <template v-else>分册还没有可用照片，加入接力留下第一张吧。</template>
              </p>
            </div>
          </div>
          <div class="guess-options">
            <button
              v-for="m in currentGuess?.options || []"
              :key="m"
              type="button"
              class="guess-option"
              :class="{
                correct: guessResult && m === guessResult.actual_month,
                wrong:
                  guessResult && picked === m && m !== guessResult.actual_month,
              }"
              :disabled="!!guessResult || !currentGuess"
              @click="answer(m)"
            >
              {{ monthLabel(m) }}
            </button>
          </div>
          <div class="guess-foot">
            <button
              class="outline"
              type="button"
              id="guess-reveal"
              :disabled="!currentGuess || !!guessResult || usedHint"
              @click="useHint"
            >
              <Lightbulb :size="15" />
              {{ usedHint ? '提示已用（-4 分）' : '用提示卡（-4 分）' }}
            </button>
            <button
              class="secondary"
              type="button"
              id="guess-next"
              :disabled="!guessResult"
              @click="nextGuess"
            >
              下一张<ArrowRight class="icon" />
            </button>
          </div>
          <div v-if="scoreboard.length" class="guess-board">
            <h3>本册排行榜</h3>
            <ol>
              <li v-for="(row, i) in scoreboard" :key="row.user_id">
                <span class="rank">{{ i + 1 }}</span>
                <span class="name">{{ row.name }}</span>
                <span class="pts">{{ row.points }} 分</span>
              </li>
            </ol>
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
  Lightbulb,
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
const guessRounds = ref([])
const guessIndex = ref(0)
const guessResult = ref(null)
const picked = ref(null)
const usedHint = ref(false)
const hintText = ref('')
const myScore = ref(0)
const scoreboard = ref([])
const timerLeft = ref(15)
const roundStart = ref(0)
let guessTimer = 0
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

const currentGuess = computed(
  () => guessRounds.value[guessIndex.value] || null,
)
const monthNames = [
  '一月', '二月', '三月', '四月', '五月', '六月',
  '七月', '八月', '九月', '十月', '十一月', '十二月',
]
const monthLabel = (m) => monthNames[(Number(m) || 1) - 1]

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
    const [roundsRes, boardRes] = await Promise.all([
      api.get(`/api/circles/${circle}/albums/${id}/guess/rounds`),
      api.get(`/api/circles/${circle}/albums/${id}/guess/scoreboard`),
    ])
    if (circle !== auth.currentCircleId || id !== props.albumId || !active)
      return
    if (!roundsRes.data.length) {
      toast('分册还没有照片，先加入接力留下第一张')
      return
    }
    guessRounds.value = roundsRes.data
    guessIndex.value = 0
    applyBoard(boardRes.data)
    resetRound()
    guessOpen.value = true
  } catch (e) {
    toast(e.userMessage || '加载猜照片失败')
  }
}

function applyBoard(data) {
  scoreboard.value = data?.scoreboard || []
  myScore.value = data?.my_score || 0
}

function stopTimer() {
  clearInterval(guessTimer)
  guessTimer = 0
}

function resetRound() {
  guessResult.value = null
  picked.value = null
  usedHint.value = false
  hintText.value = ''
  timerLeft.value = 15
  roundStart.value = Date.now()
  stopTimer()
  guessTimer = setInterval(() => {
    timerLeft.value -= 1
    if (timerLeft.value <= 0) stopTimer()
  }, 1000)
}

async function answer(month) {
  if (!currentGuess.value || guessResult.value) return
  const circle = auth.currentCircleId,
    id = props.albumId,
    mediaId = currentGuess.value.media_id,
    elapsed = Date.now() - roundStart.value
  stopTimer()
  picked.value = month
  try {
    const { data } = await api.post(
      `/api/circles/${circle}/albums/${id}/guess/answer`,
      {
        media_id: mediaId,
        guessed_month: month,
        elapsed_ms: Math.min(elapsed, 120000),
        used_hint: usedHint.value,
      },
    )
    guessResult.value = data
    myScore.value = data.my_score
    scoreboard.value = data.scoreboard
    if (data.correct) toast(`猜对了，+${data.points} 分`)
  } catch (e) {
    toast(e.userMessage || '提交答案失败')
  }
}

async function useHint() {
  if (!currentGuess.value || usedHint.value || guessResult.value) return
  try {
    const { data } = await api.get(
      `/api/circles/${auth.currentCircleId}/albums/${props.albumId}/guess/hint`,
      { params: { media_id: currentGuess.value.media_id } },
    )
    usedHint.value = true
    hintText.value = [data.season, data.author ? `${data.author} 拍的` : '', data.place]
      .filter(Boolean)
      .join(' · ')
  } catch (e) {
    toast(e.userMessage || '提示卡暂时不可用')
  }
}

function nextGuess() {
  stopTimer()
  guessIndex.value =
    guessIndex.value + 1 < guessRounds.value.length ? guessIndex.value + 1 : 0
  resetRound()
}

onActivated(() => {
  active = true
  if (loadedRevision !== revision.value) load()
})
onDeactivated(() => {
  active = false
  stopTimer()
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
