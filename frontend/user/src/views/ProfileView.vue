<template>
  <section class="profile-page" aria-label="个人主页">
    <header class="profile-heading">
      <UserAvatar
        :src="auth.user?.avatar"
        :name="name"
        class="av-coral profile-avatar"
      />
      <div class="profile-identity">
        <span class="eyebrow">MY JOURNAL / 个人主页</span>
        <h2>{{ name }}</h2>
        <span class="profile-account"
          >@{{ auth.user?.username }} · {{ auth.circles.length }} 个圈子</span
        >
      </div>
      <button
        class="icon-button"
        title="账号设置"
        aria-label="账号设置"
        @click="settingsOpen = true"
      >
        <Settings2 :size="19" />
      </button>
      <button
        class="icon-button"
        title="退出登录"
        aria-label="退出登录"
        @click="$emit('logout')"
      >
        <LogOut :size="19" />
      </button>
    </header>
    <nav class="segmented profile-tabs" aria-label="个人主页视图">
      <button
        v-for="item in tabs"
        :key="item.key"
        :class="{ active: tab === item.key }"
        @click="selectTab(item.key)"
      >
        <component :is="item.icon" :size="16" />{{ item.label }}
      </button>
    </nav>
    <KeepAlive :max="3"
      ><component
        :is="components[tab]"
        @open-post="$emit('open-post', $event)"
        @open-circle="$emit('open-circle', $event)"
        @unread="$emit('unread', $event)"
    /></KeepAlive>
    <ProfileSettings v-if="settingsOpen" @close="settingsOpen = false" />
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Bell, Bookmark, Clock3, LogOut, Settings2 } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import ActivityTimeline from '../components/ActivityTimeline.vue'
import UserAvatar from '../components/UserAvatar.vue'
import ProfileSettings from '../components/ProfileSettings.vue'
import MessageCenter from '../components/MessageCenter.vue'
import FavoritesCollection from '../components/FavoritesCollection.vue'

const props = defineProps({ profileTab: { type: String, default: 'activity' } })
const emit = defineEmits([
  'open-post',
  'logout',
  'open-circle',
  'unread',
  'profile-tab',
])
const auth = useAuthStore()
const name = computed(() => auth.user?.nickname || auth.user?.username || '我')
const tab = ref(props.profileTab),
  settingsOpen = ref(false)
const components = {
  activity: ActivityTimeline,
  messages: MessageCenter,
  favorites: FavoritesCollection,
}
const tabs = [
  { key: 'activity', label: '痕迹线', icon: Clock3 },
  { key: 'messages', label: '消息', icon: Bell },
  { key: 'favorites', label: '收藏', icon: Bookmark },
]
function selectTab(key) {
  tab.value = key
  emit('profile-tab', key)
}
watch(
  () => props.profileTab,
  (key) => {
    tab.value = key
  },
)
</script>
