<template>
  <section class="message-center" aria-label="消息中心">
    <div class="section-head">
      <h2>
        消息中心 <small>{{ unreadCount }} 未读</small>
      </h2>
      <div class="view-actions">
        <button
          class="icon-button"
          title="刷新消息"
          aria-label="刷新消息"
          :disabled="busy || loading"
          @click="load()"
        >
          <RefreshCw :size="17" />
        </button>
        <button
          class="text-button"
          :disabled="busy || !unreadCount"
          @click="readAll"
        >
          <CheckCheck :size="17" />全部已读
        </button>
      </div>
    </div>
    <div class="segmented">
      <button :class="{ active: !unreadOnly }" @click="unreadOnly = false">
        全部</button
      ><button :class="{ active: unreadOnly }" @click="unreadOnly = true">
        未读
      </button>
    </div>
    <div v-if="error" class="inline-notice" role="alert">
      <p>{{ error }}</p>
      <button class="outline" :disabled="busy" @click="load()">重试</button>
    </div>
    <div v-if="loading" class="activity-skeleton">
      <div v-for="i in 3" :key="i" class="skeleton" />
    </div>
    <template v-else>
      <div
        v-for="m in items"
        :key="m.id"
        class="message-row"
        :class="{ unread: !m.is_read }"
      >
        <span class="message-symbol"><Bell :size="18" /></span>
        <div class="social-row-copy">
          <strong>{{ m.title }}</strong>
          <p>{{ m.body }}</p>
          <small>{{ date(m.created_at) }}</small>
        </div>
        <button
          v-if="!m.is_read"
          class="icon-button"
          title="标为已读"
          aria-label="标为已读"
          :disabled="busy"
          @click="read(m)"
        >
          <Check :size="17" />
        </button>
        <button
          v-if="m.can_open_post || m.can_open_circle"
          class="icon-button"
          title="查看消息关联内容"
          aria-label="查看消息关联内容"
          :disabled="busy"
          @click="open(m)"
        >
          <ArrowUpRight :size="18" />
        </button>
      </div>
      <div v-if="!items.length && !error" class="empty-state">
        {{ unreadOnly ? '没有未读消息' : '暂无消息' }}
      </div>
      <div v-if="items.length < total" class="activity-end">
        <button class="outline" :disabled="busy" @click="load(true)">
          更早的消息
        </button>
      </div>
    </template>
  </section>
</template>
<script setup>
import { inject, onActivated, onBeforeUnmount, ref, watch } from 'vue'
import {
  ArrowUpRight,
  Bell,
  Check,
  CheckCheck,
  RefreshCw,
} from 'lucide-vue-next'
import api from '../api'
const emit = defineEmits(['open-post', 'open-circle', 'unread'])
const revision = inject('revision'),
  items = ref([]),
  total = ref(0),
  unreadCount = ref(0),
  unreadOnly = ref(false),
  loading = ref(true),
  busy = ref(false),
  error = ref('')
const date = (s) => new Date(s).toLocaleString('zh-CN')
let sequence = 0
async function load(more = false) {
  if (typeof more !== 'boolean') more = false
  const request = ++sequence
  loading.value = !more
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/me/notifications', {
      params: {
        unread: unreadOnly.value,
        offset: more ? items.value.length : 0,
      },
    })
    if (request !== sequence) return
    items.value = more ? [...items.value, ...data.items] : data.items
    total.value = data.total
    unreadCount.value = data.unread_count
    emit('unread', data.unread_count)
  } catch (e) {
    if (request === sequence) error.value = e.userMessage
  } finally {
    if (request === sequence) loading.value = busy.value = false
  }
}
async function read(m) {
  busy.value = true
  try {
    await api.put(`/api/me/notifications/${m.id}/read`)
    m.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    emit('unread', unreadCount.value)
    if (unreadOnly.value) await load()
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
async function readAll() {
  busy.value = true
  try {
    await api.put('/api/me/notifications/read-all')
    await load()
  } catch (e) {
    error.value = e.userMessage
  } finally {
    busy.value = false
  }
}
async function open(m) {
  if (!m.is_read) await read(m)
  if (m.can_open_post) emit('open-post', { id: m.post_id })
  else emit('open-circle', m.circle_id)
}
watch(unreadOnly, () => load())
watch(revision, () => load())
onActivated(load)
onBeforeUnmount(() => {
  sequence++
})
</script>
