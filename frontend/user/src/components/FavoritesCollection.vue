<template>
  <section class="favorites-collection" aria-label="我的收藏">
    <div class="section-head">
      <h2>我的收藏</h2>
      <button class="text-button" @click="newFolder">
        <Plus :size="17" />新建收藏夹
      </button>
    </div>
    <div class="segmented">
      <button :class="{ active: scope === 'mine' }" @click="scope = 'mine'">
        我的收藏夹</button
      ><button
        :class="{ active: scope === 'shared' }"
        @click="scope = 'shared'"
      >
        圈内分享
      </button>
    </div>
    <nav v-if="visibleFolders.length" class="folder-nav" aria-label="收藏夹">
      <button
        v-for="f in visibleFolders"
        :key="f.id"
        :class="{ active: selectedId === f.id }"
        @click="selectedId = f.id"
      >
        <FolderOpen :size="16" />{{ f.title }}<small>{{ f.item_count }}</small>
      </button>
    </nav>
    <div v-if="current" class="collection-toolbar">
      <div>
        <strong>{{ current.title }}</strong
        ><small>{{
          current.is_owner
            ? current.shared
              ? '指定朋友圈可见'
              : '仅自己可见'
            : `由 ${current.nickname} 分享`
        }}</small>
      </div>
      <button
        v-if="current.is_owner"
        class="icon-button"
        title="编辑收藏夹"
        aria-label="编辑收藏夹"
        @click="editFolder"
      >
        <Pencil :size="17" /></button
      ><button
        v-if="current.is_owner"
        class="icon-button danger-text"
        title="删除收藏夹"
        aria-label="删除收藏夹"
        :disabled="busy"
        @click="removeFolder"
      >
        <Trash2 :size="17" />
      </button>
    </div>
    <div v-if="loading" class="activity-skeleton">
      <div v-for="i in 3" :key="i" class="skeleton" />
    </div>
    <div v-else-if="error" class="empty-state" role="alert">
      <p>{{ error }}</p>
      <button class="outline" @click="load">重试</button>
    </div>
    <template v-else>
      <div v-for="item in items" :key="item.id" class="favorite-row">
        <button
          v-if="item.post"
          class="favorite-record"
          @click="open(item, $event)"
        >
          <div class="favorite-preview">
            <MediaPreview
              v-if="item.post.media.length"
              :media="item.post.media[0]"
              :alt="item.post.content"
            /><ImageOff v-else :size="24" />
          </div>
          <div class="social-row-copy">
            <strong>{{ item.post.content || '这一刻，没有文字。' }}</strong
            ><small
              >{{ item.post.circle_name }} · {{ item.post.event_date }}</small
            >
          </div>
        </button>
        <div v-else class="favorite-record unavailable">
          <div class="favorite-preview"><ImageOff :size="24" /></div>
          <div class="social-row-copy">
            <strong>记录不可用</strong><small>原记录已删除或当前无权访问</small>
          </div>
        </div>
        <button
          v-if="current?.is_owner"
          class="icon-button danger-text"
          title="移除收藏"
          aria-label="移除收藏"
          :disabled="busy"
          @click="removeItem(item)"
        >
          <BookmarkMinus :size="18" />
        </button>
      </div>
      <div v-if="!items.length" class="empty-state">
        {{
          current
            ? '这个收藏夹还没有记录'
            : scope === 'mine'
              ? '还没有收藏夹'
              : '暂无可见的圈内收藏夹'
        }}
      </div>
    </template>
    <FolderEditor
      v-if="editorOpen"
      :folder="editing"
      @close="editorOpen = false"
      @saved="saved"
    />
  </section>
</template>
<script setup>
import { computed, inject, onActivated, onBeforeUnmount, ref, watch } from 'vue'
import {
  BookmarkMinus,
  FolderOpen,
  ImageOff,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-vue-next'
import api from '../api'
import MediaPreview from './MediaPreview.vue'
import FolderEditor from './FolderEditor.vue'
import { confirmDialog } from '../utils/confirm'
const emit = defineEmits(['open-post'])
const revision = inject('revision'),
  folders = ref([]),
  items = ref([]),
  selectedId = ref(null),
  scope = ref('mine'),
  loading = ref(true),
  busy = ref(false),
  error = ref(''),
  editorOpen = ref(false),
  editing = ref(null)
const visibleFolders = computed(() =>
  folders.value.filter((f) => f.is_owner === (scope.value === 'mine')),
)
const current = computed(() =>
  visibleFolders.value.find((f) => f.id === selectedId.value),
)
let sequence = 0
async function load() {
  const request = ++sequence
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/me/favorite-folders')
    if (request !== sequence) return
    folders.value = data
    if (!visibleFolders.value.some((f) => f.id === selectedId.value))
      selectedId.value = visibleFolders.value[0]?.id || null
    await loadItems()
  } catch (e) {
    if (request === sequence) {
      error.value = e.userMessage
      loading.value = false
    }
  }
}
async function loadItems() {
  const request = ++sequence,
    id = selectedId.value
  loading.value = true
  error.value = ''
  items.value = []
  if (!id) {
    loading.value = false
    return
  }
  try {
    const { data } = await api.get(`/api/me/favorite-folders/${id}/items`)
    if (request === sequence) items.value = data.items
  } catch (e) {
    if (request === sequence) error.value = e.userMessage
  } finally {
    if (request === sequence) loading.value = false
  }
}
function open(item, event) {
  emit('open-post', {
    id: item.post_id,
    source: event.currentTarget.querySelector('img'),
  })
}
function newFolder() {
  editing.value = null
  editorOpen.value = true
}
function editFolder() {
  editing.value = current.value
  editorOpen.value = true
}
async function saved(f) {
  editorOpen.value = false
  scope.value = 'mine'
  selectedId.value = f.id
  revision.value++
  await load()
}
async function removeFolder() {
  const id = selectedId.value
  if (
    !(await confirmDialog({
      title: '删除收藏夹',
      message: '只删除收藏分类与收藏关系，原记录保留。',
      confirmText: '删除收藏夹',
      danger: true,
    }))
  )
    return
  busy.value = true
  try {
    await api.delete(`/api/me/favorite-folders/${id}`)
    revision.value++
    await load()
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
async function removeItem(item) {
  busy.value = true
  try {
    await api.delete(
      `/api/me/favorite-folders/${selectedId.value}/items/${item.id}`,
    )
    revision.value++
    await load()
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
watch(selectedId, loadItems)
watch(scope, () => {
  selectedId.value = visibleFolders.value[0]?.id || null
  if (!selectedId.value) {
    items.value = []
    loading.value = false
  }
})
watch(revision, load)
onActivated(load)
onBeforeUnmount(() => {
  sequence++
})
</script>
