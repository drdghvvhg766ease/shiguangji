<template>
  <Transition name="install">
    <aside v-if="visible" class="install-card" role="complementary" aria-label="安装到桌面">
      <button class="install-close" type="button" aria-label="关闭提示" @click="dismiss">
        <X :size="15" />
      </button>
      <span class="install-icon">
        <img src="/icons/icon-192.png" alt="" width="40" height="40" />
      </span>
      <div class="install-copy">
        <strong>把时光迹装到桌面</strong>
        <small v-if="iosHint">
          点 Safari 底部的分享按钮，选「添加到主屏幕」，以后打开就像 App 一样。
        </small>
        <small v-else>全屏打开、少一步输入网址，拍完照回来更快。</small>
      </div>
      <button v-if="!iosHint" class="install-action" type="button" :disabled="installing" @click="install">
        {{ installing ? '添加中…' : '添加' }}
      </button>
    </aside>
  </Transition>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'

const STORAGE_KEY = 'sgj-install-dismissed'
const COOLDOWN = 7 * 24 * 60 * 60 * 1000

const visible = ref(false)
const iosHint = ref(false)
const installing = ref(false)
let deferred = null
let timer = null

function standalone() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true
  )
}

function onBeforeInstall(event) {
  event.preventDefault()
  deferred = event
  if (!visible.value && !standalone()) visible.value = true
}

function onInstalled() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, String(Date.now()))
}

async function install() {
  if (!deferred) return
  installing.value = true
  try {
    deferred.prompt()
    const choice = await deferred.userChoice
    if (choice?.outcome === 'accepted') onInstalled()
    else dismiss()
  } catch {
    dismiss()
  } finally {
    deferred = null
    installing.value = false
  }
}

function dismiss() {
  visible.value = false
  try {
    localStorage.setItem(STORAGE_KEY, String(Date.now()))
  } catch {
    // 隐私模式下写不进去也不影响使用
  }
}

onMounted(() => {
  if (standalone()) return
  const dismissedAt = Number(localStorage.getItem(STORAGE_KEY) || 0)
  if (Date.now() - dismissedAt < COOLDOWN) return

  window.addEventListener('beforeinstallprompt', onBeforeInstall)
  window.addEventListener('appinstalled', onInstalled)

  // iOS 没有 beforeinstallprompt，改用一次性文字引导
  const ua = navigator.userAgent
  const isIOS = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document)
  if (isIOS && !window.matchMedia('(display-mode: standalone)').matches) {
    iosHint.value = true
    timer = setTimeout(() => {
      visible.value = true
    }, 6000)
  }
})

onBeforeUnmount(() => {
  clearTimeout(timer)
  window.removeEventListener('beforeinstallprompt', onBeforeInstall)
  window.removeEventListener('appinstalled', onInstalled)
})
</script>

<style scoped>
.install-card {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 78;
  display: flex;
  align-items: center;
  gap: 11px;
  width: min(340px, calc(100vw - 36px));
  padding: 11px 13px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--surface);
  color: var(--ink);
  box-shadow: var(--shadow-md);
}
.install-icon {
  flex: none;
  width: 40px;
  height: 40px;
  border-radius: 9px;
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}
.install-icon img {
  display: block;
  width: 100%;
  height: 100%;
}
.install-copy {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.install-copy strong {
  font-size: 12px;
}
.install-copy small {
  font-size: 10px;
  line-height: 1.5;
  color: var(--muted);
}
.install-action {
  flex: none;
  padding: 6px 13px;
  border: 0;
  border-radius: 7px;
  background: var(--terracotta);
  color: #fff;
  font-size: 11px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
}
.install-action:disabled {
  opacity: 0.6;
}
.install-close {
  position: absolute;
  top: -8px;
  right: -8px;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: var(--surface);
  color: var(--muted);
  box-shadow: var(--shadow-xs);
  cursor: pointer;
}
.install-close:hover {
  background: color-mix(in srgb, var(--ink) 8%, transparent);
  color: var(--ink);
}
.install-enter-active,
.install-leave-active {
  transition: opacity 0.22s ease, transform 0.22s var(--ease-out);
}
.install-enter-from,
.install-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
@media (max-width: 650px) {
  .install-card {
    right: 12px;
    left: 12px;
    bottom: calc(72px + env(safe-area-inset-bottom));
    width: auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .install-enter-active,
  .install-leave-active {
    transition: none;
  }
}
</style>
