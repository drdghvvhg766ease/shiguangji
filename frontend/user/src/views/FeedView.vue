<template>
  <section aria-label="照片墙" class="feed-page">
    <div class="page-head">
      <div>
        <span class="eyebrow"
          >{{ auth.currentCircle?.name || '我们' }} / 日常影集</span
        >
        <h1>照片墙<span class="heading-dot">.</span></h1>
        <p>{{ posts.length }} 条记录 · {{ mediaCount }} 个影像</p>
      </div>
      <button class="primary" title="发布记录" @click="$emit('nav', 'compose')">
        <Plus class="icon" />发布记录
      </button>
    </div>
    <div class="gallery-greeting">
      <span>{{ dateLabel }}</span>
      <p>{{ auth.user?.nickname || auth.user?.username }}，今天也值得记住。</p>
    </div>
    <div class="filter-row">
      <div class="segmented">
        <button
          v-for="tag in tags"
          :key="tag"
          :class="{ active: tagFilter === tag }"
          @click="tagFilter = tag"
        >
          {{ tag === 'all' ? '全部' : tag }}
        </button>
      </div>
      <div class="filters-right">
        <select
          v-model="memberFilter"
          class="field-select"
          aria-label="筛选成员"
        >
          <option :value="null">所有成员</option>
          <option v-for="m in members" :key="m.user_id" :value="m.user_id">
            {{ m.nickname || m.username }}
          </option></select
        ><select v-model="sortBy" class="field-select" aria-label="排序">
          <option value="created">最近发布</option>
          <option value="event">生活日期</option>
        </select>
      </div>
    </div>
    <div v-if="loading" class="feed-skeleton" aria-label="正在加载">
      <div v-for="i in 3" :key="i" class="skeleton" />
    </div>
    <div v-else-if="error" class="empty-state" role="alert">
      <p>{{ error }}</p>
      <button class="outline" @click="load">重试</button>
    </div>
    <template v-else-if="visible.length">
      <article class="photo-story featured-story">
        <button
          class="story-image"
          :aria-label="`打开记录：${visible[0].content}`"
          @click="open(visible[0], $event)"
        >
          <MediaPreview
            v-if="visible[0].media[0]"
            :media="visible[0].media[0]"
            :alt="visible[0].content"
            eager
          />
          <div v-else class="text-story">{{ visible[0].content }}</div>
          <span class="story-count" v-if="visible[0].media.length > 1"
            ><Images :size="14" />{{ visible[0].media.length }}</span
          ></button
        ><StoryCaption
          :post="visible[0]"
          @open="open(visible[0], $event, true)"
        />
      </article>
      <div class="photo-columns">
        <article v-for="p in visible.slice(1)" :key="p.id" class="photo-story">
          <button
            class="story-image"
            :aria-label="`打开记录：${p.content}`"
            @click="open(p, $event)"
          >
            <MediaPreview
              v-if="p.media[0]"
              :media="p.media[0]"
              :alt="p.content"
            />
            <div v-else class="text-story">{{ p.content }}</div>
            <span class="story-count" v-if="p.media.length > 1"
              ><Images :size="14" />{{ p.media.length }}</span
            ></button
          ><StoryCaption :post="p" @open="open(p, $event, true)" />
        </article>
      </div>
      <div class="collection-end">
        <span></span>把日子，留在这里。<span></span>
      </div>
    </template>
    <div v-else class="empty-state">
      {{
        !auth.currentCircleId
          ? '建立或加入圈子，开始记录。'
          : posts.length
            ? '没有符合筛选条件的记录。'
            : '还没有记录，留下第一张照片吧。'
      }}
    </div>
  </section>
</template>
<script setup>
import { computed, inject, onActivated, onDeactivated, ref, watch } from 'vue'
import { Images, Plus } from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import MediaPreview from '../components/MediaPreview.vue'
import StoryCaption from '../components/StoryCaption.vue'
const emit = defineEmits(['nav', 'open-post'])
const auth = useAuthStore(),
  revision = inject('revision')
const posts = ref([]),
  members = ref([]),
  tagFilter = ref('all'),
  memberFilter = ref(null),
  sortBy = ref('created'),
  loading = ref(true),
  error = ref('')
let request = 0,
  loadedRevision = -1,
  active = false
const tags = computed(() => [
  'all',
  ...new Set(posts.value.map((p) => p.activity_tag).filter(Boolean)),
])
const mediaCount = computed(() =>
  posts.value.reduce((n, p) => n + p.media.length, 0),
)
const dateLabel = new Intl.DateTimeFormat('en', {
  month: 'short',
  day: '2-digit',
  year: 'numeric',
})
  .format(new Date())
  .toUpperCase()
const visible = computed(() =>
  posts.value
    .filter(
      (p) =>
        (tagFilter.value === 'all' || p.activity_tag === tagFilter.value) &&
        (!memberFilter.value || p.user_id === memberFilter.value),
    )
    .sort((a, b) =>
      String(
        sortBy.value === 'event' ? b.event_date : b.created_at,
      ).localeCompare(
        String(sortBy.value === 'event' ? a.event_date : a.created_at),
      ),
    ),
)
function open(p, event, comments = false) {
  emit('open-post', {
    id: p.id,
    mediaId: p.media[0]?.id,
    source: event?.currentTarget?.closest('article')?.querySelector('img'),
    comments,
  })
}
async function load() {
  const seq = ++request,
    circle = auth.currentCircleId
  error.value = ''
  loading.value = !!circle && !posts.value.length
  if (!circle) {
    posts.value = []
    members.value = []
    return
  }
  try {
    const [p, m] = await Promise.all([
      api.get(`/api/circles/${circle}/posts`),
      api.get(`/api/circles/${circle}/members`),
    ])
    if (seq !== request || circle !== auth.currentCircleId) return
    posts.value = p.data
    members.value = m.data
    loadedRevision = revision.value
  } catch (e) {
    if (seq === request) error.value = e.userMessage || '加载失败，请重试'
  } finally {
    if (seq === request) loading.value = false
  }
}
onActivated(() => {
  active = true
  if (loadedRevision !== revision.value) load()
})
onDeactivated(() => {
  active = false
})
watch(revision, () => {
  if (active) load()
})
</script>
