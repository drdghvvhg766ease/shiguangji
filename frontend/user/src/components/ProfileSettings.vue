<template>
  <div v-dialog="close" class="modal open" @click.self="close">
    <form class="modal-card narrow" @submit.prevent="save">
      <div class="modal-head">
        <strong>账号设置</strong
        ><button
          type="button"
          class="icon-button"
          title="关闭"
          aria-label="关闭账号设置"
          :disabled="busy"
          @click="close"
        >
          <X />
        </button>
      </div>
      <div class="social-form">
        <div class="segmented">
          <button
            type="button"
            :class="{ active: mode === 'profile' }"
            @click="mode = 'profile'"
          >
            个人资料</button
          ><button
            type="button"
            :class="{ active: mode === 'password' }"
            @click="mode = 'password'"
          >
            修改密码
          </button>
        </div>
        <template v-if="mode === 'profile'">
          <button
            type="button"
            class="avatar-edit-button"
            title="修改头像"
            aria-label="修改头像"
            @click="fileInput.click()"
          >
            <UserAvatar
              :src="preview || auth.user?.avatar"
              :name="nickname"
              class="av-coral profile-avatar"
            /><Camera :size="17" />
          </button>
          <input
            ref="fileInput"
            class="visually-hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            @change="selectFile"
          />
          <label
            >昵称<input v-model="nickname" required maxlength="32"
          /></label>
        </template>
        <template v-else
          ><label
            >当前密码<input
              v-model="password.current"
              type="password"
              autocomplete="current-password"
              required /></label
          ><label
            >新密码<input
              v-model="password.next"
              type="password"
              autocomplete="new-password"
              minlength="6"
              maxlength="64"
              required /></label
          ><label
            >确认新密码<input
              v-model="password.confirm"
              type="password"
              autocomplete="new-password"
              required /></label
        ></template>
        <p v-if="error" class="error-message" role="alert">{{ error }}</p>
        <button class="primary" :disabled="busy">
          {{ busy ? '保存中…' : '保存修改' }}
        </button>
      </div>
    </form>
    <AvatarCropper
      v-if="cropFile"
      :file="cropFile"
      @close="cropFile = null"
      @cropped="cropped"
    />
  </div>
</template>
<script setup>
import { inject, onBeforeUnmount, reactive, ref } from 'vue'
import { Camera, X } from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { confirmDialog } from '../utils/confirm'
import AvatarCropper from './AvatarCropper.vue'
import UserAvatar from './UserAvatar.vue'
const emit = defineEmits(['close'])
const auth = useAuthStore(),
  revision = inject('revision'),
  toast = inject('toast')
const mode = ref('profile'),
  nickname = ref(auth.user?.nickname || ''),
  busy = ref(false),
  error = ref(''),
  cropFile = ref(null),
  avatarFile = ref(null),
  preview = ref(''),
  fileInput = ref(null)
const password = reactive({ current: '', next: '', confirm: '' })
function selectFile(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  error.value = ''
  if (
    !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) ||
    file.size > 5 * 1024 * 1024
  ) {
    error.value = '头像支持 JPEG、PNG、WebP，最大 5 MB'
    return
  }
  cropFile.value = file
}
function cropped(file) {
  if (preview.value) URL.revokeObjectURL(preview.value)
  avatarFile.value = file
  preview.value = URL.createObjectURL(file)
  cropFile.value = null
}
async function close() {
  if (busy.value) return
  if (
    (nickname.value !== auth.user?.nickname ||
      avatarFile.value ||
      password.current ||
      password.next) &&
    !(await confirmDialog({
      title: '放弃修改',
      message: '尚未保存的资料将丢失。',
      confirmText: '放弃修改',
    }))
  )
    return
  emit('close')
}
async function save() {
  if (busy.value) return
  error.value = ''
  if (mode.value === 'password' && password.next !== password.confirm) {
    error.value = '两次新密码不一致'
    return
  }
  busy.value = true
  try {
    if (mode.value === 'profile') {
      const { data } = await api.patch('/api/auth/profile', {
        nickname: nickname.value.trim(),
      })
      auth.user = data
      if (avatarFile.value) {
        const form = new FormData()
        form.append('file', avatarFile.value)
        const response = await api.post('/api/auth/avatar', form)
        auth.user = response.data
      }
      avatarFile.value = null
    } else
      await api.post('/api/auth/password', {
        current_password: password.current,
        new_password: password.next,
      })
    revision.value++
    toast('修改已保存')
    emit('close')
  } catch (e) {
    error.value = e.userMessage || '保存失败，请重试'
  } finally {
    busy.value = false
  }
}
onBeforeUnmount(() => {
  if (preview.value) URL.revokeObjectURL(preview.value)
})
</script>
