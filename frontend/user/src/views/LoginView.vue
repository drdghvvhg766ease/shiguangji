<template>
  <div class="login-image">
    <div class="login-particles css-particles" aria-hidden="true">
      <span
        v-for="(d, i) in photoDots"
        :key="'p' + i"
        class="particle"
        :style="dotStyle(d)"
      />
    </div>
    <div class="login-wordmark">
      时光迹
      <small>把一起走过的日子，留在这里。</small>
    </div>
  </div>

  <div class="login-form-wrap">
    <div class="login-particles css-particles" aria-hidden="true">
      <span
        v-for="(d, i) in formDots"
        :key="'f' + i"
        class="particle"
        :style="dotStyle(d)"
      />
    </div>

    <form class="login-form" :class="{ shake: shaking }" @submit.prevent="submit" novalidate>
      <div class="brand">
        <span class="brand-mark">迹</span>
        <span class="brand-name">时光迹</span>
      </div>

      <div :key="mode" class="mode-pane">
        <template v-if="mode === 'login'">
          <h1>欢迎回来</h1>
          <p>继续看看朋友们留下的生活片段。</p>
          <div class="form-group">
            <label for="login-name">用户名</label>
            <input
              ref="nameInput"
              id="login-name"
              v-model="username"
              placeholder="请输入用户名"
              autocomplete="username"
              required
            />
          </div>
          <div class="form-group">
            <label for="login-password">密码</label>
            <div class="password-input">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
                required
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :title="showPassword ? '隐藏密码' : '显示密码'"
                tabindex="-1"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>
          <button class="primary" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            {{ loading ? '请稍候…' : '登录' }}
          </button>
          <div class="login-register">
            还没有账号？
            <button type="button" @click="switchMode('register')">创建账号</button>
          </div>
        </template>

        <template v-else>
          <h1>创建账号</h1>
          <p>和朋友一起，把日子留下来。</p>
          <div class="form-group">
            <label for="reg-name">用户名</label>
            <input
              ref="nameInput"
              id="reg-name"
              v-model="username"
              placeholder="至少 3 个字符"
              autocomplete="username"
              required
              minlength="3"
            />
          </div>
          <div class="form-group">
            <label for="reg-nick">昵称</label>
            <input id="reg-nick" v-model="nickname" placeholder="朋友怎么称呼你" autocomplete="nickname" />
          </div>
          <div class="form-group">
            <label for="reg-pass">密码</label>
            <div class="password-input">
              <input
                id="reg-pass"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="至少 6 位"
                autocomplete="new-password"
                required
                minlength="6"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :title="showPassword ? '隐藏密码' : '显示密码'"
                tabindex="-1"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11-8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>
          <button class="primary" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            {{ loading ? '请稍候…' : '注册并进入' }}
          </button>
          <div class="login-register">
            已有账号？
            <button type="button" @click="switchMode('login')">去登录</button>
          </div>
        </template>
      </div>

      <p v-if="error" class="form-error">{{ error }}</p>
      <p class="demo-hint">演示：demo_a / demo1234 · demo_b / demo1234</p>
    </form>
  </div>
</template>

<script setup>
import { onMounted, ref, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const mode = ref('login')
const username = ref('')
const password = ref('')
const nickname = ref('')
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const shaking = ref(false)
const nameInput = ref(null)
const photoDots = ref([])
const formDots = ref([])

const PARTICLE_COLORS = ['#d76b50', '#81b29a', '#d9ab59', '#ffffff']

function makeDots(count) {
  return Array.from({ length: count }, () => ({
    left: Math.random() * 100,
    bottom: Math.random() * 35,
    size: 1 + Math.random() * 2.5,
    duration: 12 + Math.random() * 14,
    delay: -Math.random() * 20,
    drift: Math.random() * 60 - 30,
    color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)],
    peak: 0.25 + Math.random() * 0.35,
  }))
}

function dotStyle(d) {
  return {
    left: d.left + '%',
    bottom: d.bottom + '%',
    width: d.size + 'px',
    height: d.size + 'px',
    background: d.color,
    color: d.color,
    animationDuration: d.duration + 's',
    animationDelay: d.delay + 's',
    '--drift': d.drift + 'px',
    '--peak': d.peak,
  }
}

function applyPrefs() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const mobile = window.innerWidth < 650
  const n = reduce ? 0 : mobile ? 12 : 24
  photoDots.value = makeDots(n)
  formDots.value = makeDots(Math.max(8, n - 6))
}

function switchMode(target) {
  if (target === mode.value || loading.value) return
  mode.value = target
  showPassword.value = false
  error.value = ''
  nextTick(() => nameInput.value?.focus({ preventScroll: true }))
}

let shakeTimer = null
function triggerShake() {
  shaking.value = false
  nextTick(() => {
    shaking.value = true
    clearTimeout(shakeTimer)
    shakeTimer = setTimeout(() => (shaking.value = false), 520)
  })
}

onMounted(() => {
  applyPrefs()
  window.addEventListener('resize', applyPrefs)
  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', applyPrefs)
  nextTick(() => nameInput.value?.focus({ preventScroll: true }))
})

async function submit() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'login') {
      await auth.login(username.value.trim(), password.value)
    } else {
      await auth.register(username.value.trim(), password.value, nickname.value.trim())
    }
  } catch (e) {
    error.value = e.userMessage || '操作失败'
    triggerShake()
  } finally {
    loading.value = false
  }
}
</script>
