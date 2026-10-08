<template>
  <div v-if="showLogin" class="login-page active" style="display: block">
    <LoginView />
  </div>

  <div v-else class="app">
    <aside class="sidebar">
      <a href="#" class="brand" @click.prevent="go('feed')">
        <span class="brand-mark">迹</span>
        <span class="brand-name">时光迹</span>
      </a>

      <button class="circle-select" type="button" @click="go('circle')">
        <span class="circle-icon">{{ circleChar }}</span>
        <span class="circle-select-text">
          <strong>{{ auth.currentCircle?.name || '还没有圈子' }}</strong>
          <small>{{
            auth.currentCircle
              ? `${auth.currentCircle.member_count} 位成员 · 私密圈子`
              : '建立或加入一个圈子'
          }}</small>
        </span>
        <ChevronsUpDown class="icon" />
      </button>

      <div class="side-label">空间</div>
      <nav class="side-nav" aria-label="主导航">
        <button
          v-for="item in navItems"
          :key="item.view"
          type="button"
          class="nav-button"
          :class="{ active: activeView === item.view }"
          @click="go(item.view)"
        >
          <component :is="item.icon" class="icon" />
          {{ item.label }}
        </button>
      </nav>

      <button class="compose-side" type="button" @click="go('compose')">
        <Plus class="icon" />
        记录这一刻
      </button>

      <div class="side-grow"></div>

      <section class="sidebar-members">
        <h3>圈内成员</h3>
        <div class="avatar-row">
          <span
            v-for="m in members.slice(0, 6)"
            :key="m.user_id"
            class="avatar"
            :class="avatarClass(m.user_id)"
            :title="m.nickname || m.username"
          >
            {{ (m.nickname || m.username || '?').slice(0, 1) }}
          </span>
        </div>
      </section>

      <button
        class="sidebar-user"
        :class="{ active: activeView === 'profile' }"
        type="button"
        title="个人主页"
        aria-label="个人主页"
        @click="go('profile')"
      >
        <UserAvatar
          :src="auth.user?.avatar"
          :name="auth.user?.nickname"
          class="av-coral"
        />
        <strong>{{ auth.user?.nickname || auth.user?.username }}</strong>
        <UserRound class="icon" />
      </button>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="breadcrumbs">
          <span>{{
            activeView === 'profile'
              ? '我的空间'
              : auth.currentCircle?.name || '时光迹'
          }}</span>
          <ChevronRight class="icon" />
          <strong>{{ title }}</strong>
        </div>
        <div class="top-actions">
          <span class="today">{{ todayLabel }}</span>
          <button
            class="icon-button notification-entry"
            title="消息中心"
            :aria-label="`消息中心${unreadCount ? `，${unreadCount}条未读` : ''}`"
            @click="goMessages"
          >
            <Bell :size="20" /><span v-if="unreadCount" class="unread-badge">{{
              unreadCount > 99 ? '99+' : unreadCount
            }}</span>
          </button>
          <span class="avatar av-coral top-avatar">{{
            (auth.user?.nickname || '?').slice(0, 1)
          }}</span>
        </div>
      </header>

      <header class="mobile-top">
        <a href="#" class="brand" @click.prevent="go('feed')">
          <span class="brand-mark">迹</span>
          <span class="brand-name">时光迹</span>
        </a>
        <div class="mobile-account-actions">
          <button
            class="text-button circle-label"
            type="button"
            @click="go('circle')"
          >
            {{ auth.currentCircle?.name || '圈子' }}
            <ChevronDown class="icon" /></button
          ><button
            class="icon-button notification-entry"
            title="消息中心"
            aria-label="消息中心"
            @click="goMessages"
          >
            <Bell :size="19" /><span v-if="unreadCount" class="unread-badge">{{
              unreadCount > 99 ? '99+' : unreadCount
            }}</span></button
          ><button
            class="icon-button profile-entry"
            :class="{ active: activeView === 'profile' }"
            aria-label="个人主页"
            title="个人主页"
            @click="go('profile')"
          >
            <UserRound :size="20" />
          </button>
        </div>
      </header>

      <div ref="scrollContainer" class="body-grid">
        <main class="main-column">
          <Transition name="view" mode="out-in" @after-enter="restoreScroll">
            <KeepAlive
              :key="`${auth.user?.id}-${auth.currentCircleId}`"
              :max="12"
            >
              <component
                :is="viewComponent"
                :key="viewKey"
                class="view-wrap"
                :album-id="albumId"
                :preset-album-id="presetAlbumId"
                :profile-tab="profileTab"
                @nav="go"
                @open-album="openAlbum"
                @back="go('album')"
                @compose="composeToAlbum"
                @published="onPublished"
                @logout="logout"
                @profile-tab="profileTab = $event"
                @unread="unreadCount = $event"
                @open-circle="openCircle"
                @open-post="detailRequest = $event"
              />
            </KeepAlive>
          </Transition>
        </main>

        <aside
          v-if="activeView === 'profile'"
          class="right-rail"
          aria-label="我的圈子"
        >
          <section class="rail-section">
            <h2>
              我的圈子 <span>{{ auth.circles.length }} 个</span>
            </h2>
            <div class="profile-circle-list">
              <button
                v-for="circle in auth.circles"
                :key="circle.id"
                type="button"
                @click="openCircleTimeline(circle.id)"
              >
                <UsersRound :size="18" /><span
                  >{{ circle.name
                  }}<small>{{ circle.member_count }} 位成员</small></span
                ><ArrowUpRight :size="16" />
              </button>
            </div>
          </section>
        </aside>
        <aside v-else class="right-rail" aria-label="圈子信息">
          <section class="rail-section">
            <h2>
              主题分册 <span>共 {{ albums.length }} 本</span>
            </h2>
            <template v-if="featured">
              <div class="mini-cover">
                <img
                  v-for="(id, i) in (featured.cover_thumbs || []).slice(0, 3)"
                  :key="i"
                  :src="`/api/media/${id}/file?variant=preview`"
                  alt=""
                  loading="lazy"
                  decoding="async"
                />
                <img
                  v-if="!(featured.cover_thumbs || []).length"
                  src="/preview-assets/graduates.jpg"
                  alt=""
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <div class="rail-album-title">
                <div>
                  <strong>{{ featured.title }}</strong>
                  <small
                    >{{ featured.post_count }} 条记录 ·
                    {{ featured.participant_count }} 位朋友参与</small
                  >
                </div>
                <button
                  class="rail-link"
                  type="button"
                  title="打开分册"
                  @click="openAlbum(featured.id)"
                >
                  <ArrowUpRight class="icon" />
                </button>
              </div>
              <p v-if="featured.prompt" class="prompt">{{ featured.prompt }}</p>
            </template>
            <p v-else class="rail-note">
              还没有主题分册，去共同相册创建一本吧。
            </p>
          </section>

          <section class="rail-section">
            <h2>
              圈内成员 <span>{{ members.length }} 人</span>
            </h2>
            <div class="member-list">
              <div v-for="m in members" :key="m.user_id" class="member-line">
                <span class="avatar" :class="avatarClass(m.user_id)">{{
                  (m.nickname || '?').slice(0, 1)
                }}</span>
                <span>{{ m.nickname || m.username }}</span>
                <small>{{
                  m.role === 'owner'
                    ? '圈主'
                    : m.role === 'admin'
                      ? '管理员'
                      : '成员'
                }}</small>
              </div>
            </div>
          </section>

          <div class="rail-quote">下一次见面，也记得留一张照片。</div>
        </aside>
      </div>
    </div>
  </div>

  <nav v-if="!showLogin" class="mobile-nav" aria-label="手机端导航">
    <button
      v-for="item in mobileNav"
      :key="item.view"
      type="button"
      :class="{ active: activeView === item.view }"
      :data-view="item.view"
      @click="go(item.view)"
    >
      <span v-if="item.view === 'compose'" class="mobile-compose-icon"
        ><Plus class="icon"
      /></span>
      <component v-else :is="item.icon" class="icon" />
      {{ item.label }}
    </button>
  </nav>

  <div class="toast" :class="{ show: toastMsg }" role="status">
    {{ toastMsg }}
  </div>
  <RecordDetail
    v-if="detailRequest"
    :request="detailRequest"
    @close="detailRequest = null"
    @changed="onDetailChanged"
  />
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  provide,
  ref,
  watch,
} from 'vue'
import {
  ArrowUpRight,
  Bell,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Clock3,
  Images,
  LayoutGrid,
  Plus,
  UsersRound,
  UserRound,
} from 'lucide-vue-next'
import { useAuthStore } from './stores/auth'
import api from './api'
import LoginView from './views/LoginView.vue'
import FeedView from './views/FeedView.vue'
import TimelineView from './views/TimelineView.vue'
import AlbumView from './views/AlbumView.vue'
import AlbumDetailView from './views/AlbumDetailView.vue'
import ComposeView from './views/ComposeView.vue'
import CircleView from './views/CircleView.vue'
import ProfileView from './views/ProfileView.vue'
import RecordDetail from './components/RecordDetail.vue'
import UserAvatar from './components/UserAvatar.vue'

const auth = useAuthStore()
const activeView = ref('feed')
const profileTab = ref('activity'),
  unreadCount = ref(0)
const albumId = ref(null)
const presetAlbumId = ref(null)
const members = ref([])
const albums = ref([])
const toastMsg = ref('')
const scrollContainer = ref(null)
const detailRequest = ref(null)
const revision = ref(0)
const draftGuard = ref(null)
const scrollPositions = new Map()
const viewComponent = computed(
  () =>
    ({
      feed: FeedView,
      timeline: TimelineView,
      album: AlbumView,
      'album-detail': AlbumDetailView,
      compose: ComposeView,
      circle: CircleView,
      profile: ProfileView,
    })[activeView.value],
)
const viewKey = computed(
  () =>
    activeView.value +
    (activeView.value === 'album-detail' ? `-${albumId.value}` : ''),
)
provide('revision', revision)
provide('draftGuard', draftGuard)
let toastTimer,
  railSequence = 0

const navItems = [
  { view: 'feed', label: '照片墙', icon: LayoutGrid },
  { view: 'timeline', label: '生活痕迹线', icon: Clock3 },
  { view: 'album', label: '共同相册', icon: Images },
  { view: 'circle', label: '圈子', icon: UsersRound },
]
const mobileNav = [
  { view: 'feed', label: '照片墙', icon: LayoutGrid },
  { view: 'timeline', label: '时间轴', icon: Clock3 },
  { view: 'compose', label: '发布', icon: Plus },
  { view: 'album', label: '相册', icon: Images },
  { view: 'circle', label: '圈子', icon: UsersRound },
]

const titleMap = {
  feed: '照片墙',
  timeline: '生活痕迹线',
  album: '共同相册',
  'album-detail': '主题分册',
  compose: '记录这一刻',
  circle: '圈子',
  profile: '个人主页',
}

const showLogin = computed(() => {
  if (!auth.loaded) return true
  return !auth.user
})
const title = computed(() => titleMap[activeView.value] || '照片墙')
const circleChar = computed(() =>
  (auth.currentCircle?.name || '圈').slice(0, 1),
)
const featured = computed(() => albums.value[0] || null)

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
})

function avatarClass(id) {
  return ['av-coral', 'av-teal', 'av-gold', 'av-green'][Number(id || 0) % 4]
}

function showToast(msg, ms = 2200) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    if (toastMsg.value === msg) toastMsg.value = ''
  }, ms)
}
provide('toast', showToast)

async function canLeave() {
  return !draftGuard.value || (await draftGuard.value())
}
function saveScroll() {
  scrollPositions.set(viewKey.value, scrollContainer.value?.scrollTop || 0)
}
function restoreScroll() {
  nextTick(() =>
    scrollContainer.value?.scrollTo({
      top: scrollPositions.get(viewKey.value) || 0,
      behavior: 'instant',
    }),
  )
}
async function go(view) {
  if (view === activeView.value) return
  if (!(await canLeave())) return
  saveScroll()
  activeView.value = view
  if (view !== 'album-detail') albumId.value = null
  if (view !== 'compose') presetAlbumId.value = null
}

async function openCircleTimeline(id) {
  if (!(await canLeave())) return
  auth.setCurrentCircle(id)
  await go('timeline')
}

async function goMessages() {
  await go('profile')
  if (activeView.value === 'profile') profileTab.value = 'messages'
}
async function openCircle(id) {
  if (!(await canLeave())) return
  try {
    await auth.fetchCircles()
    if (!auth.circles.some((c) => c.id === id)) {
      showToast('该圈子暂不可访问')
      return
    }
    auth.setCurrentCircle(id)
    await go('circle')
  } catch (e) {
    showToast(e.userMessage || '打开圈子失败')
  }
}
let notificationTimer,
  notificationSequence = 0
async function loadNotifications() {
  const request = ++notificationSequence,
    user = auth.user
  if (!user) {
    unreadCount.value = 0
    return
  }
  try {
    const { data } = await api.get('/api/me/notifications', {
      params: { limit: 1 },
    })
    if (request === notificationSequence && auth.user?.id === user.id)
      unreadCount.value = data.unread_count
  } catch {
    /* A failed badge refresh does not interrupt the current view. */
  }
}

async function openAlbum(id) {
  if (!(await canLeave())) return
  saveScroll()
  albumId.value = id
  activeView.value = 'album-detail'
}

async function composeToAlbum(id) {
  if (!(await canLeave())) return
  saveScroll()
  presetAlbumId.value = id
  activeView.value = 'compose'
}

function onPublished(album) {
  revision.value++
  if (album) openAlbum(album)
  else go('feed')
}
function onDetailChanged() {
  saveScroll()
  revision.value++
}

async function logout() {
  if (!(await canLeave())) return
  try {
    await auth.logout()
    activeView.value = 'feed'
  } catch (e) {
    showToast(e.userMessage || '退出失败，请重试')
  }
}

async function loadRail() {
  const sequence = ++railSequence
  const circle = auth.currentCircleId
  if (!auth.currentCircleId) {
    members.value = []
    albums.value = []
    return
  }
  try {
    const [mRes, aRes] = await Promise.all([
      api.get(`/api/circles/${circle}/members`),
      api.get(`/api/circles/${circle}/albums`),
    ])
    if (sequence !== railSequence || circle !== auth.currentCircleId) return
    members.value = mRes.data
    albums.value = aRes.data
  } catch {
    /* rail is non-blocking */
  }
}

watch(
  () => auth.currentCircleId,
  () => {
    detailRequest.value = null
    members.value = []
    albums.value = []
    scrollPositions.clear()
    albumId.value = null
    presetAlbumId.value = null
    if (activeView.value === 'album-detail') activeView.value = 'album'
    revision.value++
    loadRail()
    restoreScroll()
  },
)
watch(revision, loadRail)
watch(revision, loadNotifications)
watch(
  () => auth.user?.id,
  () => {
    profileTab.value = 'activity'
    loadNotifications()
  },
)

onMounted(async () => {
  await auth.fetchMe()
  if (auth.user) {
    auth.restoreCircle()
    await auth.fetchCircles()
    await loadRail()
    await loadNotifications()
  }
  notificationTimer = setInterval(() => {
    if (!document.hidden) loadNotifications()
  }, 30000)
})
onBeforeUnmount(() => {
  clearInterval(notificationTimer)
  notificationSequence++
  clearTimeout(toastTimer)
})
</script>
