<template>
  <div v-dialog="close" class="modal open" @click.self="close">
    <form class="modal-card narrow" @submit.prevent="save">
      <div class="modal-head">
        <strong>收藏到</strong
        ><button
          type="button"
          class="icon-button"
          title="关闭"
          aria-label="关闭收藏选择"
          :disabled="busy"
          @click="close"
        >
          <X />
        </button>
      </div>
      <div class="social-form">
        <div v-if="loading" class="skeleton picker-loading"></div>
        <label
          v-for="f in folders"
          :key="f.id"
          class="checkbox-label folder-pick-row"
          ><input v-model="selected" type="checkbox" :value="f.id" /><Folder
            :size="18" /><span>{{ f.title }}</span
          ><Lock v-if="!f.shared" :size="14" /><UsersRound v-else :size="14"
        /></label>
        <p v-if="!loading && !folders.length" class="muted">还没有收藏夹</p>
        <button type="button" class="text-button" @click="creating = true">
          <Plus :size="16" />新建收藏夹
        </button>
        <p v-if="error" class="error-message" role="alert">
          {{ error
          }}<button type="button" class="text-button" @click="load">
            重试加载
          </button>
        </p>
        <button class="primary" :disabled="busy || loading || !folders.length">
          {{ busy ? '保存中…' : '保存收藏' }}
        </button>
      </div>
    </form>
    <FolderEditor v-if="creating" @close="creating = false" @saved="created" />
  </div>
</template>
<script setup>
import { inject, onMounted, ref } from 'vue'
import { Folder, Lock, Plus, UsersRound, X } from 'lucide-vue-next'
import api from '../api'
import FolderEditor from './FolderEditor.vue'
const props = defineProps({ postId: { type: Number, required: true } })
const emit = defineEmits(['close', 'saved'])
const revision = inject('revision'),
  folders = ref([]),
  selected = ref([]),
  loading = ref(true),
  busy = ref(false),
  creating = ref(false),
  error = ref('')
function close() {
  if (!busy.value) emit('close')
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/me/favorite-folders', {
      params: { post_id: props.postId },
    })
    folders.value = data.filter((f) => f.is_owner)
    selected.value = folders.value
      .filter((f) => f.contains_post)
      .map((f) => f.id)
  } catch (e) {
    error.value = e.userMessage
  } finally {
    loading.value = false
  }
}
function created(f) {
  creating.value = false
  folders.value.unshift(f)
  selected.value.push(f.id)
}
async function save() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    for (const f of folders.value) {
      if (selected.value.includes(f.id) && !f.contains_post) {
        const { data } = await api.put(
          `/api/me/favorite-folders/${f.id}/items`,
          { post_id: props.postId },
        )
        f.contains_post = true
        f.item_id = data.id
      } else if (!selected.value.includes(f.id) && f.contains_post) {
        await api.delete(`/api/me/favorite-folders/${f.id}/items/${f.item_id}`)
        f.contains_post = false
      }
    }
    revision.value++
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>
