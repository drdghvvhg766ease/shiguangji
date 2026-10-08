<template>
  <section class="circle-management">
    <div v-if="error" class="inline-notice" role="alert">
      {{ error }}<button class="text-button" @click="load">重试</button>
    </div>
    <section v-if="requests.length" class="social-section">
      <div class="section-head">
        <h2>入圈申请</h2>
        <span>{{ requests.length }} 待审核</span>
      </div>
      <div v-for="r in requests" :key="r.id" class="social-row">
        <div class="social-row-copy">
          <strong>{{ r.nickname || r.username }}</strong>
          <p>{{ r.message || '申请加入圈子' }}</p>
          <small>{{ date(r.created_at) }}</small>
        </div>
        <button class="outline" :disabled="busy" @click="approve(r)">
          <Check :size="16" />通过
        </button>
        <button
          class="text-button danger-text"
          :disabled="busy"
          @click="rejecting = r"
        >
          <X :size="16" />拒绝
        </button>
      </div>
    </section>
    <section v-if="auth.currentCircleId" class="social-section">
      <div class="section-head">
        <h2>圈子公告</h2>
        <button
          v-if="auth.canManage"
          class="text-button"
          @click="announcementOpen = true"
        >
          <Plus :size="16" />发布公告
        </button>
      </div>
      <p v-if="!announcements.length" class="muted">暂无公告</p>
      <article v-for="a in announcements" :key="a.id" class="announcement-row">
        <div class="social-row">
          <h3>{{ a.title }}</h3>
          <button
            v-if="auth.canManage"
            class="icon-button danger-text"
            title="删除公告"
            aria-label="删除公告"
            :disabled="busy"
            @click="removeAnnouncement(a)"
          >
            <Trash2 :size="17" />
          </button>
        </div>
        <p>{{ a.content }}</p>
        <small>{{ a.nickname }} · {{ date(a.created_at) }}</small>
      </article>
    </section>
    <section v-if="auth.canManage" class="social-section">
      <div class="section-head">
        <h2>成员管理</h2>
        <span>{{ members.length }} 人</span>
      </div>
      <div
        v-for="m in members"
        :key="m.user_id"
        class="social-row member-management-row"
      >
        <div class="social-row-copy">
          <strong>{{ m.nickname || m.username }}</strong
          ><small>{{ roles[m.role] }}</small>
        </div>
        <template v-if="m.user_id !== auth.user?.id && m.role !== 'owner'">
          <button
            v-if="auth.isOwner"
            class="icon-button"
            :title="m.role === 'admin' ? '撤销管理员' : '设为管理员'"
            :aria-label="`${m.role === 'admin' ? '撤销管理员' : '设为管理员'}：${m.nickname}`"
            :disabled="busy"
            @click="setRole(m)"
          >
            <ShieldOff v-if="m.role === 'admin'" :size="18" /><ShieldCheck
              v-else
              :size="18"
            />
          </button>
          <button
            v-if="auth.isOwner"
            class="icon-button"
            title="转让圈主"
            :aria-label="`转让圈主给：${m.nickname}`"
            :disabled="busy"
            @click="transfer(m)"
          >
            <Crown :size="18" />
          </button>
          <button
            v-if="auth.isOwner || m.role === 'member'"
            class="icon-button danger-text"
            title="移出成员"
            :aria-label="`移出成员：${m.nickname}`"
            :disabled="busy"
            @click="removeMember(m)"
          >
            <UserMinus :size="18" />
          </button>
        </template>
      </div>
    </section>
    <section v-if="mine.length" class="social-section">
      <div class="section-head"><h2>我的入圈申请</h2></div>
      <div v-for="r in mine" :key="r.id" class="social-row">
        <div class="social-row-copy">
          <strong>{{ r.circle_name }}</strong>
          <p v-if="r.review_reason">{{ r.review_reason }}</p>
        </div>
        <span class="status-label" :class="r.status">{{
          statuses[r.status]
        }}</span>
      </div>
    </section>
    <div
      v-if="announcementOpen"
      v-dialog="closeAnnouncement"
      class="modal open"
      @click.self="closeAnnouncement"
    >
      <form class="modal-card narrow" @submit.prevent="publish">
        <div class="modal-head">
          <strong>发布圈子公告</strong
          ><button
            type="button"
            class="icon-button"
            title="关闭"
            aria-label="关闭公告编辑"
            :disabled="busy"
            @click="closeAnnouncement"
          >
            <X />
          </button>
        </div>
        <div class="social-form">
          <label
            >公告标题<input
              v-model="announcement.title"
              maxlength="80"
              required /></label
          ><label
            >公告内容<textarea
              v-model="announcement.content"
              maxlength="2000"
              rows="6"
              required
            />
          </label>
          <p v-if="error" class="error-message">{{ error }}</p>
          <button class="primary" :disabled="busy">
            {{ busy ? '发布中…' : '发布公告' }}
          </button>
        </div>
      </form>
    </div>
    <div
      v-if="rejecting"
      v-dialog="closeReject"
      class="modal open"
      @click.self="closeReject"
    >
      <form class="modal-card narrow" @submit.prevent="reject">
        <div class="modal-head">
          <strong>拒绝入圈申请</strong
          ><button
            type="button"
            class="icon-button"
            title="关闭"
            aria-label="关闭拒绝申请"
            :disabled="busy"
            @click="closeReject"
          >
            <X />
          </button>
        </div>
        <div class="social-form">
          <label
            >审核说明<textarea v-model="reason" maxlength="200" rows="3" />
          </label>
          <p v-if="error" class="error-message">{{ error }}</p>
          <button class="primary" :disabled="busy">
            {{ busy ? '提交中…' : '确认拒绝' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>
<script setup>
import { inject, onActivated, onBeforeUnmount, reactive, ref, watch } from 'vue'
import {
  Check,
  Crown,
  Plus,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserMinus,
  X,
} from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { confirmDialog } from '../utils/confirm'
defineProps({ members: { type: Array, default: () => [] } })
const emit = defineEmits(['refresh'])
const auth = useAuthStore(),
  revision = inject('revision'),
  toast = inject('toast')
const mine = ref([]),
  requests = ref([]),
  announcements = ref([]),
  error = ref(''),
  busy = ref(false)
const announcementOpen = ref(false),
  rejecting = ref(null),
  reason = ref('')
const announcement = reactive({ title: '', content: '' })
const roles = { owner: '圈主', admin: '管理员', member: '普通成员' }
const statuses = { pending: '等待审核', approved: '已通过', rejected: '未通过' }
const date = (s) =>
  new Date(s).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
let sequence = 0
async function load() {
  const request = ++sequence,
    circle = auth.currentCircleId
  error.value = ''
  try {
    const [m, a, r] = await Promise.all([
      api.get('/api/circles/join-requests/mine'),
      circle
        ? api.get(`/api/circles/${circle}/announcements`)
        : Promise.resolve({ data: [] }),
      circle && auth.canManage
        ? api.get(`/api/circles/${circle}/join-requests`)
        : Promise.resolve({ data: [] }),
    ])
    if (request !== sequence || circle !== auth.currentCircleId) return
    mine.value = m.data
    announcements.value = a.data
    requests.value = r.data
  } catch (e) {
    if (request === sequence) error.value = e.userMessage || '加载失败'
  }
}
async function perform(fn) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await fn()
    await auth.fetchCircles()
    emit('refresh')
    revision.value++
    await load()
  } catch (e) {
    error.value = e.userMessage || '操作失败，请重试'
  } finally {
    busy.value = false
  }
}
function approve(r) {
  const circle = auth.currentCircleId
  perform(() =>
    api.patch(`/api/circles/${circle}/join-requests/${r.id}`, {
      status: 'approved',
    }),
  )
}
function reject() {
  const circle = auth.currentCircleId
  perform(async () => {
    await api.patch(
      `/api/circles/${circle}/join-requests/${rejecting.value.id}`,
      { status: 'rejected', reason: reason.value },
    )
    rejecting.value = null
    reason.value = ''
  })
}
function publish() {
  const circle = auth.currentCircleId
  perform(async () => {
    await api.post(`/api/circles/${circle}/announcements`, announcement)
    announcementOpen.value = false
    announcement.title = announcement.content = ''
    toast('公告已发布')
  })
}
function closeAnnouncement() {
  if (!busy.value) announcementOpen.value = false
}
function closeReject() {
  if (!busy.value) {
    rejecting.value = null
    reason.value = ''
  }
}
async function setRole(m) {
  const circle = auth.currentCircleId,
    role = m.role === 'admin' ? 'member' : 'admin'
  if (
    !(await confirmDialog({
      title: role === 'admin' ? '设为管理员' : '撤销管理员',
      message: m.nickname || m.username,
    }))
  )
    return
  if (circle !== auth.currentCircleId) return
  perform(() =>
    api.patch(`/api/circles/${circle}/members/${m.user_id}/role`, { role }),
  )
}
async function removeMember(m) {
  const circle = auth.currentCircleId
  if (
    !(await confirmDialog({
      title: '移出成员',
      message: `${m.nickname} 将无法访问圈内内容，原记录保留。`,
      confirmText: '移出成员',
      danger: true,
    }))
  )
    return
  if (circle !== auth.currentCircleId) return
  perform(() => api.delete(`/api/circles/${circle}/members/${m.user_id}`))
}
async function transfer(m) {
  const circle = auth.currentCircleId
  if (
    !(await confirmDialog({
      title: '转让圈主',
      message: `将圈主转让给 ${m.nickname}，你将成为普通成员。`,
      confirmText: '确认转让',
    }))
  )
    return
  if (circle !== auth.currentCircleId) return
  perform(() =>
    api.post(`/api/circles/${circle}/transfer`, { user_id: m.user_id }),
  )
}
watch(
  () => auth.currentCircleId,
  () => {
    mine.value = []
    requests.value = []
    announcements.value = []
    announcementOpen.value = false
    rejecting.value = null
    load()
  },
)
watch(revision, load)
onActivated(load)
onBeforeUnmount(() => {
  sequence++
})
</script>
