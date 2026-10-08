<template>
  <section aria-label="圈子">
    <div v-if="loadError" class="empty-state" role="alert">
      <p>{{ loadError }}</p>
      <button class="outline" @click="load">重试</button>
    </div>
    <div class="mobile-account">
      <span>{{ auth.user?.nickname || auth.user?.username }}</span
      ><button class="text-button" type="button" @click="$emit('logout')">
        <LogOut :size="16" />退出登录
      </button>
    </div>
    <div class="page-head">
      <div>
        <span class="eyebrow">朋友们的小小空间</span>
        <h1>{{ current?.name || '还没有圈子' }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <button
        class="outline"
        type="button"
        data-toast="圈子设置"
        @click="showSettings = true"
      >
        <Settings2 class="icon" />
        圈子设置
      </button>
    </div>

    <template v-if="current">
      <div class="circle-panel">
        <span class="circle-icon">{{
          (current.name || '圈').slice(0, 1)
        }}</span>
        <div>
          <h2>{{ current.name }}</h2>
          <p>{{ current.description || '一起好好记住那些日子。' }}</p>
        </div>
        <button class="outline" type="button" @click="showSwitch = true">
          <ChevronsUpDown class="icon" />
          切换圈子
        </button>
      </div>

      <div class="invite-box">
        <div>
          <strong>邀请朋友加入</strong>
          <small>分享邀请码，让朋友来到这个圈子</small>
        </div>
        <button
          class="outline"
          type="button"
          id="copy-invite"
          title="复制邀请码"
          @click="copyInvite"
        >
          <span class="invite-code">{{ current.invite_code }}</span>
          <Copy class="icon" />
        </button>
      </div>

      <div class="section-head">
        <h2>圈内成员</h2>
        <span class="eyebrow">共 {{ members.length }} 人</span>
      </div>
      <div class="circle-members-grid">
        <div v-for="m in members" :key="m.user_id" class="circle-member">
          <span class="avatar" :class="avatarClass(m.user_id)">{{
            (m.nickname || '?').slice(0, 1)
          }}</span>
          <div>
            <strong>{{ m.nickname || m.username }}</strong>
            <small
              >{{
                m.role === 'owner'
                  ? '圈主'
                  : m.role === 'admin'
                    ? '管理员'
                    : '成员'
              }}
              · {{ formatDay(m.joined_at) }}加入</small
            >
          </div>
        </div>
      </div>
    </template>

    <!-- 建圈 / 加入 -->
    <div v-else class="compose-form">
      <div class="form-split">
        <div>
          <h2 style="font-family: 'Noto Serif SC', serif; font-size: 18px">
            建立我的朋友圈
          </h2>
          <p style="color: var(--muted); font-size: 12px">
            创建后你会成为圈主，并获得邀请码。
          </p>
          <div class="form-group">
            <label>圈名</label>
            <input v-model="createForm.name" placeholder="例如：我们仨" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <input
              v-model="createForm.description"
              placeholder="一起好好记住那些日子"
            />
          </div>
          <button
            class="primary"
            type="button"
            :disabled="!createForm.name.trim()"
            @click="createCircle"
          >
            创建圈子
          </button>
        </div>
        <div>
          <h2 style="font-family: 'Noto Serif SC', serif; font-size: 18px">
            凭邀请码加入
          </h2>
          <p style="color: var(--muted); font-size: 12px">
            向朋友要一串邀请码就好。
          </p>
          <div class="form-group">
            <label>邀请码</label>
            <input v-model="joinCode" placeholder="例如 DEMO2026" />
          </div>
          <button
            class="secondary"
            type="button"
            :disabled="!joinCode.trim()"
            @click="joinCircle"
          >
            加入圈子
          </button>
        </div>
      </div>
    </div>

    <CircleManagement :members="members" @refresh="load" />
    <!-- 切换圈子 -->
    <div
      v-if="showSwitch"
      v-dialog="() => (showSwitch = false)"
      class="modal open"
      @click.self="showSwitch = false"
    >
      <div class="modal-card narrow">
        <div class="modal-head">
          <strong>切换圈子</strong>
          <button class="more" type="button" @click="showSwitch = false">
            <X class="icon" />
          </button>
        </div>
        <div class="flow-body">
          <button
            v-for="c in auth.circles"
            :key="c.id"
            class="created-album"
            type="button"
            @click="switchTo(c.id)"
          >
            <div>
              <strong>{{ c.name }}</strong>
              <small
                >{{ c.member_count }} 位成员 ·
                {{ c.is_owner ? '我是圈主' : '我是成员' }}</small
              >
            </div>
            <span v-if="c.id === auth.currentCircleId" class="eyebrow"
              >当前</span
            >
          </button>
          <div class="form-group" style="margin-top: 16px">
            <label>或建立新圈子</label>
            <input v-model="createForm.name" placeholder="新圈名" />
          </div>
          <div class="flow-footer">
            <button class="outline" type="button" @click="showSwitch = false">
              关闭
            </button>
            <button
              class="primary"
              type="button"
              :disabled="!createForm.name.trim()"
              @click="createCircle"
            >
              创建并切换
            </button>
          </div>
          <div class="form-group">
            <label>凭邀请码加入其他圈子</label
            ><input v-model="joinCode" placeholder="邀请码" /><button
              class="secondary"
              type="button"
              :disabled="busy || !joinCode.trim()"
              @click="joinCircle"
            >
              加入圈子
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 圈子设置 -->
    <div
      v-if="showSettings"
      v-dialog="() => (showSettings = false)"
      class="modal open"
      @click.self="showSettings = false"
    >
      <div class="modal-card narrow">
        <div class="modal-head">
          <strong>圈子设置</strong>
          <button class="more" type="button" @click="showSettings = false">
            <X class="icon" />
          </button>
        </div>
        <div class="flow-body">
          <div class="form-group">
            <label>圈名</label>
            <input v-model="settingsForm.name" :disabled="!current?.is_owner" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <input
              v-model="settingsForm.description"
              :disabled="!current?.is_owner"
            />
          </div>
          <div class="form-group">
            <label>邀请码</label>
            <div style="display: flex; gap: 8px; align-items: center">
              <span class="invite-code">{{ current?.invite_code }}</span>
              <button
                v-if="current?.can_manage"
                class="outline"
                type="button"
                @click="rotateInvite"
              >
                重置
              </button>
            </div>
          </div>
          <div v-if="current?.is_owner" class="form-group">
            <label>危险操作</label>
            <button class="outline" type="button" @click="dissolve">
              解散圈子
            </button>
          </div>
          <button
            v-else
            class="outline"
            type="button"
            :disabled="busy"
            @click="leaveCircle"
          >
            退出圈子
          </button>
          <div class="flow-footer">
            <button class="outline" type="button" @click="showSettings = false">
              关闭
            </button>
            <button
              v-if="current?.is_owner"
              class="primary"
              type="button"
              :disabled="busy"
              @click="saveSettings"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { ChevronsUpDown, Copy, LogOut, Settings2, X } from 'lucide-vue-next'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { confirmDialog } from '../utils/confirm'
import CircleManagement from '../components/CircleManagement.vue'

const auth = useAuthStore()
defineEmits(['logout'])
const toast = inject('toast')
const loadError = ref('')
const revision = inject('revision'),
  busy = ref(false)
let sequence = 0

const members = ref([])
const showSwitch = ref(false)
const showSettings = ref(false)
const createForm = reactive({ name: '', description: '' })
const joinCode = ref('')
const settingsForm = reactive({
  name: '',
  description: '',
  allow_member_invite: false,
})

const current = computed(() => auth.currentCircle)
const subtitle = computed(() => {
  if (!current.value) return '建立自己的朋友圈，或凭邀请码加入朋友的圈子'
  const d = new Date(current.value.created_at)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月创建 · 私密圈子`
})

function avatarClass(id) {
  return ['av-coral', 'av-teal', 'av-gold', 'av-green'][Number(id || 0) % 4]
}

function formatDay(s) {
  const d = new Date(s)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
}

async function load() {
  const seq = ++sequence
  loadError.value = ''
  try {
    await auth.fetchCircles()
  } catch (e) {
    if (seq === sequence) loadError.value = e.userMessage || '加载圈子失败'
    return
  }
  const circle = auth.currentCircleId
  if (!circle) {
    members.value = []
    return
  }
  let data
  try {
    const response = await api.get(`/api/circles/${circle}/members`)
    data = response.data
  } catch (e) {
    toast(e.userMessage || '加载圈子失败')
    if (seq === sequence) loadError.value = e.userMessage || '加载圈子失败'
    return
  }
  if (seq !== sequence || circle !== auth.currentCircleId) return
  members.value = data
  if (current.value) {
    settingsForm.name = current.value.name
    settingsForm.description = current.value.description || ''
    settingsForm.allow_member_invite = !!current.value.allow_member_invite
  }
}

async function createCircle() {
  if (busy.value) return
  busy.value = true
  try {
    const { data } = await api.post('/api/circles', {
      name: createForm.name.trim(),
      description: createForm.description.trim(),
    })
    toast(`圈子「${data.name}」已创建`)
    createForm.name = ''
    createForm.description = ''
    auth.setCurrentCircle(data.id)
    showSwitch.value = false
    await load()
  } catch (e) {
    toast(e.userMessage || '创建失败')
  } finally {
    busy.value = false
  }
}

async function joinCircle() {
  if (busy.value) return
  busy.value = true
  try {
    const { data } = await api.post('/api/circles/join', {
      invite_code: joinCode.value.trim(),
    })
    toast(`已申请加入「${data.circle_name}」，等待审核`)
    joinCode.value = ''
    revision.value++
    await load()
  } catch (e) {
    toast(e.userMessage || '加入失败')
  } finally {
    busy.value = false
  }
}

function switchTo(id) {
  auth.setCurrentCircle(id)
  showSwitch.value = false
  load()
}

async function copyInvite() {
  try {
    await navigator.clipboard.writeText(current.value.invite_code)
    toast(`邀请码已复制：${current.value.invite_code}`)
  } catch {
    toast(`邀请码：${current.value.invite_code}`)
  }
}

async function rotateInvite() {
  const ok = await confirmDialog({
    title: '重置邀请码',
    message: '旧邀请码立即失效，需重新分享。',
    confirmText: '重置',
    danger: true,
  })
  if (!ok) return
  try {
    const { data } = await api.post(
      `/api/circles/${auth.currentCircleId}/invite-code/rotate`,
    )
    toast(`新邀请码：${data.invite_code}`)
    await load()
    revision.value++
  } catch (e) {
    toast(e.userMessage || '重置失败')
  }
}

async function saveSettings() {
  if (busy.value) return
  busy.value = true
  try {
    await api.patch(`/api/circles/${auth.currentCircleId}/settings`, {
      name: settingsForm.name.trim(),
      description: settingsForm.description.trim(),
      allow_member_invite: settingsForm.allow_member_invite,
    })
    toast('设置已保存')
    showSettings.value = false
    await load()
    revision.value++
  } catch (e) {
    toast(e.userMessage || '保存失败')
  } finally {
    busy.value = false
  }
}

async function dissolve() {
  if (busy.value) return
  const ok = await confirmDialog({
    title: '解散圈子',
    message: '将删除该圈全部记录、照片与视频，不可恢复。',
    confirmText: '解散',
    danger: true,
  })
  if (!ok) return
  busy.value = true
  try {
    await api.delete(`/api/circles/${auth.currentCircleId}`)
    toast('圈子已解散')
    auth.setCurrentCircle(null)
    showSettings.value = false
    await load()
  } catch (e) {
    toast(e.userMessage || e.response?.data?.detail || '操作失败')
  } finally {
    busy.value = false
  }
}

async function leaveCircle() {
  if (
    busy.value ||
    !(await confirmDialog({
      title: '退出圈子',
      message: '退出后将无法查看圈内记录。',
      confirmText: '退出圈子',
      danger: true,
    }))
  )
    return
  busy.value = true
  try {
    await api.delete(
      `/api/circles/${auth.currentCircleId}/members/${auth.user.id}`,
    )
    auth.setCurrentCircle(null)
    await load()
    toast('已退出圈子')
  } catch (e) {
    toast(e.userMessage || '退出失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
watch(() => auth.currentCircleId, load)
</script>
