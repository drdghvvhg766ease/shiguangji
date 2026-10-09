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

    <form class="login-form" @submit.prevent="submit">
      <div class="brand">
        <span class="brand-mark">迹</span>
        <span class="brand-name">时光迹</span>
      </div>

      <template v-if="mode === 'login'">
        <h1>欢迎回来</h1>
        <p>继续看看朋友们留下的生活片段。</p>
        <div class="form-group">
          <label for="login-name">用户名</label>
          <input id="login-name" v-model="username" placeholder="请输入用户名" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label for="login-password">密码</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            required
          />
        </div>
        <button class="primary" type="submit" :disabled="loading">
          {{ loading ? '请稍候…' : '登录' }}
        </button>
        <div class="login-register">
          还没有账号？
          <button type="button" @click="mode = 'register'">创建账号</button>
        </div>
      </template>

      <template v-else>
        <h1>创建账号</h1>
        <p>和朋友一起，把日子留下来。</p>
        <div class="form-group">
          <label for="reg-name">用户名</label>
          <input id="reg-name" v-model="username" placeholder="至少 3 个字符" required minlength="3" />
        </div>
        <div class="form-group">
          <label for="reg-nick">昵称</label>
          <input id="reg-nick" v-model="nickname" placeholder="朋友怎么称呼你" />
        </div>
        <div class="form-group">
          <label for="reg-pass">密码</label>
          <input id="reg-pass" v-model="password" type="password" placeholder="至少 6 位" required minlength="6" />
        </div>
        <button class="primary" type="submit" :disabled="loading">
          {{ loading ? '请稍候…' : '注册并进入' }}
        </button>
        <div class="login-register">
          已有账号？
          <button type="button" @click="mode = 'login'">去登录</button>
        </div>
      </template>

      <p v-if="error" style="color: var(--terracotta-dark); font-size: 12px; margin-top: 12px">{{ error }}</p>
      <p style="color: var(--muted); font-size: 11px; margin-top: 18px">
        演示：demo_a / demo1234 · demo_b / demo1234
      </p>
    </form>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const mode = ref('login')
const username = ref('')
const password = ref('')
const nickname = ref('')
const loading = ref(false)
const error = ref('')
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

onMounted(() => {
  applyPrefs()
  window.addEventListener('resize', applyPrefs)
  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', applyPrefs)
})

async function submit() {
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
  } finally {
    loading.value = false
  }
}
</script>
