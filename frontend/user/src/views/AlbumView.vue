<template>
  <section aria-label="共同相册">
    <div class="page-head">
      <div>
        <span class="eyebrow">COLLECTION / 共同收藏</span>
        <h1>共同相册<span class="heading-dot">.</span></h1>
        <p>{{ items.length }} 个影像 · {{ albums.length }} 本主题分册</p>
      </div>
      <button class="primary" title="创建分册" @click="showCreate = true">
        <Plus class="icon" />创建分册
      </button>
    </div>
    <div class="filter-row">
      <div class="segmented">
        <button :class="{ active: tab === 'all' }" @click="tab = 'all'">
          全部影像</button
        ><button :class="{ active: tab === 'albums' }" @click="tab = 'albums'">
          主题分册
        </button>
      </div>
      <div class="filters-right">
        <select v-model="month" class="field-select" aria-label="筛选月份">
          <option value="">全部月份</option>
          <option v-for="m in monthOptions" :key="m">{{ m }}</option></select
        ><select v-model="member" class="field-select" aria-label="筛选成员">
          <option :value="null">所有成员</option>
          <option v-for="m in members" :key="m.user_id" :value="m.user_id">
            {{ m.nickname || m.username }}
          </option>
        </select>
      </div>
    </div>
    <div v-if="loading" class="feed-skeleton"><div class="skeleton" /></div>
    <div v-else-if="error" class="empty-state">
      <p>{{ error }}</p>
      <button class="outline" @click="load">重试</button>
    </div>
    <template v-else>
      <div class="created-albums">
        <button
          v-for="a in albums"
          :key="a.id"
          class="created-album"
          @click="$emit('open-album', a.id)"
        >
          <div>
            <strong>{{ a.title }}</strong
            ><small
              >{{ a.post_count }} 条记录 ·
              {{ a.participant_count }} 位朋友</small
            >
          </div>
          <ArrowUpRight :size="20" />
        </button>
      </div>
      <div v-if="tab === 'albums' && !albums.length" class="empty-state">
        还没有主题分册，创建一本属于你们的影集。
      </div>
      <template v-if="tab === 'all'"
        ><div v-if="featured" class="album-hero">
          <div class="album-hero-copy">
            <small
              >主题分册 / {{ featured.participant_count }} 位朋友参与</small
            >
            <h2>{{ featured.title }}</h2>
            <p>{{ featured.prompt }}</p>
            <button class="outline" @click="$emit('open-album', featured.id)">
              打开分册<ArrowUpRight class="icon" />
            </button>
          </div>
          <div class="album-hero-photos">
            <img
              v-for="id in featured.cover_thumbs.slice(0, 4)"
              :key="id"
              :src="`/api/media/${id}/file?variant=preview`"
              alt="分册封面"
              loading="lazy"
            />
            <div v-if="!featured.cover_thumbs.length" class="media-placeholder">
              等待第一张照片
            </div>
          </div>
        </div>
        <div class="section-head">
          <h2>我们的影像</h2>
          <span class="eyebrow">{{ filtered.length }} 个影像</span>
        </div>
        <div class="album-grid">
          <button
            v-for="item in filtered"
            :key="item.media.id"
            :aria-label="`打开记录：${item.content}`"
            @click="open(item, $event)"
          >
            <MediaPreview :media="item.media" :alt="item.content" />
          </button>
        </div>
        <div v-if="!filtered.length" class="empty-state">
          {{
            items.length
              ? '没有符合筛选条件的影像。'
              : '还没有影像，发布一条记录吧。'
          }}
        </div></template
      >
    </template>
    <div
      v-if="showCreate"
      v-dialog="() => (showCreate = false)"
      class="modal open"
      @click.self="showCreate = false"
    >
      <form class="modal-card narrow" @submit.prevent="createAlbum">
        <div class="modal-head">
          <strong>创建主题分册</strong
          ><button
            class="icon-button"
            type="button"
            title="关闭"
            aria-label="关闭"
            @click="showCreate = false"
          >
            <X />
          </button>
        </div>
        <div class="flow-body">
          <div class="form-group">
            <label for="new-album-title">标题</label
            ><input
              id="new-album-title"
              v-model="form.title"
              maxlength="64"
              required
            />
          </div>
          <div class="form-group">
            <label for="new-album-prompt">接力题目（可选）</label
            ><input
              id="new-album-prompt"
              v-model="form.prompt"
              maxlength="200"
            />
          </div>
          <div class="form-group">
            <label for="new-album-line">归属时间线</label
            ><select id="new-album-line" v-model="form.line_id">
              <option :value="null">汇总主线</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.title }}
              </option>
            </select>
          </div>
          <p v-if="createError" class="error-message">{{ createError }}</p>
          <div class="flow-footer">
            <button
              class="outline"
              type="button"
              :disabled="creating"
              @click="showCreate = false"
            >
              取消</button
            ><button class="primary" :disabled="creating || !form.title.trim()">
              {{ creating ? '创建中…' : '创建' }}
            </button>
          </div>
        </div>
      </form>
    </div>
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
import { ArrowUpRight, Plus, X } from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import MediaPreview from '../components/MediaPreview.vue'
const emit = defineEmits(['open-album', 'open-post'])
const auth = useAuthStore(),
  toast = inject('toast'),
  revision = inject('revision')
const items = ref([]),
  albums = ref([]),
  members = ref([]),
  tab = ref('all'),
  month = ref(''),
  member = ref(null),
  loading = ref(true),
  error = ref(''),
  showCreate = ref(false),
  creating = ref(false),
  createError = ref('')
const form = reactive({ title: '', prompt: '', line_id: null })
const lines = ref([])
const featured = computed(() => albums.value[0])
const monthOptions = computed(() =>
  [...new Set(items.value.map((i) => i.event_date.slice(0, 7)))]
    .sort()
    .reverse(),
)
const filtered = computed(() =>
  items.value.filter(
    (i) =>
      (!month.value || i.event_date.startsWith(month.value)) &&
      (!member.value || i.user_id === member.value),
  ),
)
let sequence = 0,
  loadedRevision = -1,
  active = false
function open(item, event) {
  emit('open-post', {
    id: item.post_id,
    mediaId: item.media.id,
    source: event.currentTarget.querySelector('img'),
  })
}
async function load() {
  const seq = ++sequence,
    circle = auth.currentCircleId
  error.value = ''
  loading.value = !!circle && !items.value.length && !albums.value.length
  if (!circle) {
    items.value = []
    albums.value = []
    members.value = []
    return
  }
  try {
    const [i, a, m, l] = await Promise.all([
      api.get(`/api/circles/${circle}/album`),
      api.get(`/api/circles/${circle}/albums`),
      api.get(`/api/circles/${circle}/members`),
      api.get(`/api/circles/${circle}/lines`),
    ])
    if (seq !== sequence || circle !== auth.currentCircleId) return
    items.value = i.data
    albums.value = a.data
    members.value = m.data
    lines.value = l.data
    loadedRevision = revision.value
  } catch (e) {
    if (seq === sequence) error.value = e.userMessage || '加载相册失败'
  } finally {
    if (seq === sequence) loading.value = false
  }
}
async function createAlbum() {
  if (creating.value) return
  creating.value = true
  createError.value = ''
  try {
    const { data } = await api.post(
      `/api/circles/${auth.currentCircleId}/albums`,
      {
        title: form.title.trim(),
        prompt: form.prompt.trim(),
        line_id: form.line_id,
      },
    )
    showCreate.value = false
    form.title = ''
    form.prompt = ''
    revision.value++
    toast('分册已创建')
    emit('open-album', data.id)
  } catch (e) {
    createError.value = e.userMessage || '创建失败'
  } finally {
    creating.value = false
  }
}
onActivated(() => {
  active = true
  if (loadedRevision !== revision.value) load()
})
onDeactivated(() => {
  active = false
  showCreate.value = false
})
watch(revision, () => {
  if (active) load()
})
</script>
