<template>
  <div v-dialog="close" class="modal open" @click.self="close">
    <form class="modal-card narrow" @submit.prevent="save">
      <div class="modal-head">
        <strong>{{ folder ? '编辑收藏夹' : '新建收藏夹' }}</strong
        ><button
          type="button"
          class="icon-button"
          title="关闭"
          aria-label="关闭收藏夹编辑"
          :disabled="busy"
          @click="close"
        >
          <X />
        </button>
      </div>
      <div class="social-form">
        <label
          >收藏夹名称<input v-model="title" required maxlength="64" /></label
        ><label class="checkbox-label"
          ><input v-model="shared" type="checkbox" />向指定朋友圈分享</label
        >
        <div v-if="shared" class="folder-share-options">
          <label v-for="c in auth.circles" :key="c.id" class="checkbox-label"
            ><input v-model="selectedCircles" type="checkbox" :value="c.id" />{{
              c.name
            }}</label
          >
          <p v-if="!auth.circles.length" class="muted">暂无可分享的圈子</p>
        </div>
        <p v-if="error" class="error-message" role="alert">{{ error }}</p>
        <button class="primary" :disabled="busy">
          {{ busy ? '保存中…' : '保存收藏夹' }}
        </button>
      </div>
    </form>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
const props = defineProps({ folder: { type: Object, default: null } })
const emit = defineEmits(['close', 'saved'])
const auth = useAuthStore(),
  title = ref(props.folder?.title || ''),
  selectedCircles = ref([...(props.folder?.share_circle_ids || [])]),
  shared = ref(!!selectedCircles.value.length),
  busy = ref(false),
  error = ref('')
function close() {
  if (!busy.value) emit('close')
}
async function save() {
  if (busy.value) return
  error.value = ''
  if (shared.value && !selectedCircles.value.length) {
    error.value = '请选择可见圈子'
    return
  }
  busy.value = true
  try {
    const data = {
      title: title.value.trim(),
      share_circle_ids: shared.value ? selectedCircles.value : [],
    }
    const response = props.folder
      ? await api.patch(`/api/me/favorite-folders/${props.folder.id}`, data)
      : await api.post('/api/me/favorite-folders', data)
    emit('saved', response.data)
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
</script>
